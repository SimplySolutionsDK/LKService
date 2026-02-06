# Introduction

The example integration demo is written in javascript and run with node.js.

# Prerequisites

Node and npm are required to run the example.

# Configuration

To configure the example, a file called app.env must be present. This file must contain the following values:

```sh
OAUTH_REALM = <realm>
OAUTH_CLIENT_ID = <client_id>
OAUTH_CLIENT_SECRET = <client_secret>
OAUTH_SERVER_ROOT = <server_root>
OAUTH_SCOPE = <scope>
GRAPHQL_ENDPOINT = <endpoint>
```

# Getting up and running

Install the dependencies and start the server by typing

```sh
$ cd example
$ npm install -d
$ node integration.js
```

# Credentials
To log into the example application, two hardcoded users are available: "foo" and "bar". Both users have password "password".