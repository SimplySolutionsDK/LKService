#!/usr/bin/env node
const fs = require('fs')
const express = require('express')
const htmlEncode = require('htmlencode').htmlEncode
const querystring = require('querystring')
const axios = require('axios').default
const propertiesReader = require('properties-reader');
const session = require('express-session')
const bodyParser = require('body-parser')

const app = express()
const port = 3000

// These are the site- and context-specific settings
let loadedProperties = fs.existsSync("app.env") ? propertiesReader('app.env') : undefined

// environment variables take precedence over loaded properties
let properties = {
    clientId: process.env.OAUTH_CLIENT_ID || loadedProperties.get("OAUTH_CLIENT_ID"),
    clientSecret: process.env.OAUTH_CLIENT_SECRET || loadedProperties.get("OAUTH_CLIENT_SECRET"),
    oauth2Scope: process.env.OAUTH_SCOPE || loadedProperties.get("OAUTH_SCOPE"),
    oauth2ServerRoot: process.env.OAUTH_SERVER_ROOT || loadedProperties.get("OAUTH_SERVER_ROOT"),
    oauth2ServerRealm: process.env.OAUTH_REALM || loadedProperties.get("OAUTH_REALM"),
    graphqlEndpoint: process.env.GRAPHQL_ENDPOINT || loadedProperties.get("GRAPHQL_ENDPOINT"),
    marketplaceEndpoint : process.env.MARKETPLACE_ENDPOINT || loadedProperties.get("MARKETPLACE_ENDPOINT")
}

// This is example.com's (fake) user database
let validUsers = {
    foo: "password",
    bar: "password"
}

// Enable session data in express
app.use(session({
    secret: 'supersecret',
    cookie: {},
    resave: false,
    saveUninitialized: true,
}))

function getLessorOpenIDEndpoint(endpoint) {
    return new URL(
        `${properties.oauth2ServerRoot}/auth/realms/${properties.oauth2ServerRealm}` +
        `/protocol/openid-connect/${endpoint}`
    )
}

function getFullRequestURL(req) {
    return new URL(req.protocol + '://' + req.get('host') + req.originalUrl);
}

function getRedirectUri(req) {
    let callbackUri = getFullRequestURL(req)
    callbackUri.pathname = 'callback'
    callbackUri.search = ''
    if (req.query.return_uri)
        callbackUri.searchParams.append("return_uri", req.query.return_uri)
    return callbackUri.toString()
}

function getLoginUri(req) {
    let loginUri = getFullRequestURL(req)
    let origPathname = loginUri.pathname
    loginUri.pathname = 'login'
    loginUri.search = ''
    if (origPathname !== '/' || Object.keys(req.query).length > 0) {
        let postLoginUri = getFullRequestURL(req)
        loginUri.searchParams.append('post_login_uri', postLoginUri)
    }
    return loginUri
}

// The main page
app.get('/', (req, res) => {
    if (!req.session.loggedIn) {
        res.redirect(getLoginUri(req))
        return
    }

    let redirect_uri = getRedirectUri(req)
    let url = getLessorOpenIDEndpoint("auth")
    url.searchParams.append("response_type", "code")
    url.searchParams.append("client_id", properties.clientId)
    url.searchParams.append("scope", properties.oauth2Scope)
    url.searchParams.append("redirect_uri", redirect_uri)
    res.setHeader('Content-Type', 'text/html');

    let hasTokens = req.session.tokens != null;

    res.send(rootBody(url, hasTokens));
})

// Login page
app.get('/login', (req, res) => {
    res.send(loginBody(req.query.post_login_uri))
});

// Logoff page
app.get('/logoff', (req, res) => {
    req.session.loggedIn = false;
    res.redirect("login");
});

// Helper page to get new access token via refresh token
app.get('/refreshtoken', (req, res) => {

    let url = getLessorOpenIDEndpoint("token")

    let postData = querystring.stringify({
        grant_type: "refresh_token",
        client_id: properties.clientId,
        client_secret: properties.clientSecret,
        refresh_token: req.session.tokens.refresh_token,
    })

    axios.post(url.toString(), postData)
        .then((axRes) => {
            console.log("New access token acquired via refresh token");
            req.session.tokenTime = Date.now();
            req.session.tokens.access_token = axRes.data.access_token;
            res.redirect(req.query.uri_redirect);
        })
        .catch((err) => {
            console.log("Error acquiring refresh token: ", err);
        })
});

// Helper function for executing a GraphQL query
function callGraphql(req, resp, query, variables, successFunc) {
    // Time to get a new access token?
    let now = Date.now();
    let expireTime = (req.session.tokenTime + (req.session.tokens.expires_in * 1000)) - 5000; // We subtract 5 secs. for uncertainty

    if (now >= expireTime) {
        // If token expired, redirect to page to fetch new one and redirect back to this page.
        console.log("Access token needs to be refreshed");
        let uri = req.url.substr(1);
        resp.redirect(`/refreshtoken?uri_redirect=${uri}`);
        return;
    }

    let accessToken = req.session.tokens.access_token;

    let axiosConfig = {
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            "Authorization": "Bearer " + accessToken,
        }
    };

    axios.post(properties.graphqlEndpoint, JSON.stringify({query, variables}), axiosConfig)
        .then((axRes) => {
            successFunc(axRes);
        })
        .catch((err) => {
            console.log("Error posting GraphQL query: ", err);
        })
}

// GraphQL List Employees page
app.get('/listemployees', (req, res) => {
    const queryString = "{companies{employees{name,birth_date}}}";
    callGraphql(req, res, queryString, {}, (data) => {
        res.send(graphqlResult("List Employees", queryString, data));
    });
})

// GraphQL List Companies page
app.get('/listcompanies', (req, res) => {
    const queryString = "{companies{name}}";
    callGraphql(req, res, queryString, {}, (data) => {
        res.send(graphqlResult("List Companies", queryString, data));
    });
})

// GraphQL List Pay Parts page
app.get('/listpayparts', (req, res) => {
    const companyQuery = '{ companies { id } }'
    callGraphql(req, res, companyQuery, {}, (data) => {
        const result = data.data.data;
        const companyId = result["companies"][0]["id"]

        const payPartsQuery = 'query($company_id: ID!) { pay_parts(company_id: $company_id) { code company { id } } }';
        const variables = {"company_id": companyId}
        callGraphql(req, res, payPartsQuery, variables, (data) => {
            res.send(graphqlResult("List Payparts", payPartsQuery, data));
        });
    })
})

let urlencodedParser = bodyParser.urlencoded({extended: false})
app.post('/login-submit', urlencodedParser, (req, res) => {
    if (req.body &&
        req.body.username &&
        req.body.password &&
        validUsers[req.body.username] &&
        validUsers[req.body.username] === req.body.password
    ) {
        req.session.loggedIn = true
    }
    let postLoginUri = req.body.post_login_uri ? req.body.post_login_uri : '/';
    res.redirect(postLoginUri)
})

app.get('/disconnect', (req, res) => {
    // we're stateless so we do nothing but redirect back to the return uri
    let returnUri = req.query.return_uri
    res.redirect(returnUri)
})

// Helper function for acquiring the necessary OAUTH Access token
function exchangeCodeForOAuth2Token(code, redirect_uri) {
    let url = getLessorOpenIDEndpoint("token")

    let postData = querystring.stringify({
        grant_type: "authorization_code",
        client_id: properties.clientId,
        client_secret: properties.clientSecret,
        redirect_uri: redirect_uri,
        code: code
    })

    return axios.post(url.toString(), postData)
}

app.get('/callback', (req, res) => {
    if (!req.session.loggedIn) {
        throw new Error("Expected to be logged in here")
    }
    if (req.query.error) {
        console.log("*Error*:", req.query.error);
        res.send("Error:" + req.query.error)
        return;
    }
    exchangeCodeForOAuth2Token(req.query.code, getRedirectUri(req))
        .then(function (response) {
            console.log("Got tokens", response.data);
            req.session.tokenTime = Date.now();
            req.session.tokens = response.data;

            let successURL = `${req.protocol}://${req.get('host')}/success`

            if (req.query.return_uri) {
                // If we need to redirect back to calling marketplace, success endpoint needs to know
                successURL += `?return_uri=${encodeURIComponent(req.query.return_uri)}`
            }

            let jsonAccessToken = JSON.stringify(req.session.tokens.access_token);
            res.redirect(`${properties.marketplaceEndpoint}/select-company?token=${jsonAccessToken}&return_uri=${encodeURIComponent(successURL)}`);

        })
        .catch(function (error) {
            console.log("*Error*:", error);
            res.send("Error:" + error)
        });
})


app.get('/success', (req, res) => {
    if (!req.session.loggedIn) {
        throw new Error("Expected to be logged in here")
    }

    let return_uri = req.query["return_uri"];

    // Upon success a code is provided as URL parameter, this needs to be exchanged to access/refresh tokens
    let code = req.query["code"];
    let url = `${properties.marketplaceEndpoint}/code2token/${code}`;

    axios.get(url)
        .then((axRes) => {
            req.session.tokenTime = Date.now();

            req.session.tokens.access_token = axRes.data.access_token;
            req.session.tokens.refresh_token = axRes.data.refresh_token;

            if(return_uri) {
                res.redirect(return_uri);
            }
            else {
                res.send(successBody(req.session.tokens));
            }

        })
        .catch((err) => {
            console.log("Error converting code to token", err);
        })
})

app.listen(port, () => {
    console.log(`Example app listening at http://localhost:${port}`)
})

// Helper function for display of GraphQL result
function graphqlResult(title, query, result) {
    result = result.data.data;
    const prettyResult = JSON.stringify(result, null, 4);

    return pageTemplate(`
        <h1>${title}</h1><br/>
        <h4>GraphQL Query:</h4>
        <div class="bg-light" style="padding:5px">
        <pre>${query}</pre>
        </div>
        <br/><br/>
        <h4>Result:</h4>
        <div class="bg-light" style="padding:5px">
        <pre>${prettyResult}</pre>
        </div><br/>
        <p><a class="btn btn-primary btn-lg" href="/"><< Back</a></p>
    `);
}

function pageTemplate(body) {
    return `
<!doctype html>
<html lang="en">
<head>
    <title>Example.com - Demo integration with Danløn</title>
    <link rel="stylesheet" href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css">
</head>
<body>
    <div class="jumbotron jumbotron-fluid">
        <div class="container">
            <div class="row">
                <div class="col-sm">
                    <h1 class="display-4">Example.com</h1>
                    <p class="lead">A demo of integration with Lessor</p>
                </div>
                <div class="col-sm">
                    <img height="161" width="334" src="https://rmhakron.org/wp-content/uploads/2017/02/example-logo.jpg" alt="example-logo">
                </div>
            </div>
        </div>
    </div>
    <div class="container">
${body}
    </div>
</body>
</html>
`
}

// Helper function that builds the main screen
function rootBody(integrationURL, hasTokens) {
    let body = `
        <h1>Integration with Danløn</h1>
        <p>Danløn is the best payroll app!</p>
        <p><a class="btn btn-primary btn-lg" href="${htmlEncode(integrationURL.toString())}">Integrate with Lessor</a></p>`

    let queries = `
        <p><a class="btn btn-primary btn-lg" href="listemployees">List employees</a></p>
        <p><a class="btn btn-primary btn-lg" href="listcompanies">List companies</a></p>
        <p><a class="btn btn-primary btn-lg" href="listpayparts">List payparts</a></p>`;

    let logoff = `<p><a href="logoff">Log off</a></p>`;

    return pageTemplate(!hasTokens ? body + logoff : body + queries + logoff);
}

// Helper function that builds the login screen
function loginBody(postLoginUri) {
    let returnUriInput = ''
    if (postLoginUri) {
        returnUriInput = `<input type="hidden" name="post_login_uri" value="${htmlEncode(postLoginUri)}">`
    }
    return pageTemplate(`
        <style>
            .form-signin {
                width: 100%;
                max-width: 330px;
                padding: 15px;
                margin: 0 auto;
            }
        </style>
        <form class="form-signin" action="/login-submit" method="POST">
              <h1 class="h3 mb-3 font-weight-normal">Please Log In</h1>
              <label for="inputEmail" class="sr-only">Email address</label>
              <input type="username" name="username" class="form-control mb-1" placeholder="User Name" required autofocus>
              <label for="inputPassword" class="sr-only">Password</label>
              <input type="password" name="password" class="form-control mb-1" placeholder="Password" required>
              ${returnUriInput}
              <button class="btn btn-lg btn-primary btn-block" type="submit">Log In</button>
        </form>
    `)
}

// Helper function that builds the page displayed upon successful integration
function successBody(data) {
    return pageTemplate(`
        <h1>Integration with Danløn <i>Complete!</i></h1>
        <p>
            Example.com can now use the
            <a href="http://jwt.io?token=${data.access_token}" target="_blank">
                <code>access_token</code>
            </a>
            and
            <a href="http://jwt.io?token=${data.refresh_token}" target="_blank">
                <code>refresh_token</code>
            </a>
            and store them in a database for later use.
        </p>
        <p><a class="btn btn-primary btn-lg" href="/"><< Back</a></p>
    `)
}
