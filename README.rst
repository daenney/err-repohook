##########
GithubHook
##########

GithubHook is a webhook endpoint for Err_ as well as a set of commands to
configure the routing of messages to chatrooms.

This plugin does not depend on anything but Err_ itself and the Python
standard library.

The supported Python versions are:

  * Python 2.7.7+
  * Python 3.3+

Python versions prior to 2.7 aren't supported by Err_ and Python versions
prior to Python 2.7.7 miss the `hmac.compare_digest` method to securely
and in constant time compare two digests. This is needed to validate
incoming requests as coming from Github.

Webhooks
--------

Webhooks are a way for websites, or really any service, to notify another
service that something happened. Github provides webhooks that based on
an event send a payload over HTTP to another service which can then react
accordingly.

They enable near real-time notifications of actions, so if someone pushes
code to a repository Github will send a HTTP payload with some information
about that event.

This mechanism can be used to receive almost instantaneous notifications of
activity that happens on a repository on Github. It's a great way to hook up
your repository to Err_.

Security
--------

In order to be able to validate that incoming requests are coming from
Github and not someone else who's discovered your webhooks endpoint, we
need to be able to validate the signature of the message.

This requires you to configure a secret token for each repository you
activate the webhook for. How to do so is explained in this entry on
`Securing your webhooks`_. Please disregard the comment about exposing
that value as an environment variable afterwards.

Out of security concerns this plugin will not accept unsigned messages
and if received simply throw them away. There is no setting to override
this behaviour.

This plugin tries its best to behave as a good netizen and in a lot of cases
we return error codes when something went wrong. In some cases however we
decide to accept the message but just silently throw it away. This usually
happens when the user hasn't fully configured the plugin yet.

For example, if we receive a message for a repository that is unknown to us
we simply accept it but disregard the message. This avoids us first doing
expensive computation to validate a hash to only later come to the conclusion
that we have no route for this message.

Installation
------------

To be able to use webhooks with Err_ you'll need to configure its
built-in webserver first using the `!webserver` command once you've loaded
the webserver plugin.

We **strongly** advise you to not expose the webserver plugin directly to
the internet but instead put it behind a proxying nginx or Apache HTTPD
and let those handle terminating SSL traffic for you and passing the
request on to Err_'s webserver.

The webhook on Github needs to be configured to send a payload to
https://your-endoint.tld/github with a Content type of `application/json`.

In order to install this plugin all you need to do is:

.. code-block:: text

   !repos install https://github.com/daenney/err-githubhook.git

Configuration
-------------

Most Err_ plugins can be configured using the `!config PluginName` action.
However, since this plugin has to handle fairly complex configuration
separate commands were created for you to set everything up and interact
with this plugin's settings.

To view the full configuration of the plugin you can issue the following:

.. code-block:: text

   !github config

There is no way to manipulate the configuration through this command, only
view it. Since its output contains sensitive data, like the tokens, it is
restricted to users with administrative privileges.

route
^^^^^

The `route` command is the first to be executed when adding a new repository
for which events will be forwarded. It takes as arguments the repository
and the channel you want messages routed to:

.. code-block:: text

   !github route example/example example@example.com

By default we will forward the following types of events to that channel:

  * An issue is opened/closed/changed
  * Someone comments on an issue
  * Someone comments on a commit
  * Code is pushed
  * A pull request is raised
  * A review is left on a change in a pull request

You can also pass in which events should be routed at creation time:

.. code-block:: text

   !github route example/example example@example.com push issues comment

Changing these events later simply requires you to call this command again.
Omitting the events when a route already exists resets the route to the
default events.

routes
^^^^^^

In order to list all the routes for a repository:

.. code-block:: text

   !github routes example/example

You can pass multiple repositories to `!github routes` by separating them
with a space. In return you'll get the route configuration for every of those
repositories.

.. code-block:: text

   !github routes example/example test/test

If you want to list all routes simply call the command with no arguments:

.. code-block:: text

   !github routes

default events
^^^^^^^^^^^^^^

The default events to subscribe on can be altered:

.. code-block:: text

   !github defaults push commit issues pull_request

Changing the default will only affect new routes, existing ones will have
to be updated manually using the `events` command.

Issuing that same command without any events will list the currently active
defaults:

.. code-block:: text

   !github defaults

token
^^^^^

Once you've added a route you need to configure the token for the repository.
This token is used for all routes of this repository and only needs to be set
up once.

We **strongly** advise you to do this in a private session with the bot that is
not being logged anywhere so your token doesn't accidentally show up in
places it shouldn't.

.. code-block:: text

   !github token example/example TOKEN

It is not possible to request the token once it is set. If you believe it
was set incorrectly, simply set it again to what it should be.

As explained in the above Security section, setting a token and configuring it
on the webhook is required for events to be validated and routed.

remove
^^^^^^

In order to remove a route issue the following:

.. code-block:: text

   !github remove example/example example@example.com

If this is the last route we know about for that repository any further
configuration entries for that repository will be removed too, like the
token.

Should you wish to remove all routes, essentially removing the repository:

.. codeb-lock:: text

   !github remove example/example

This will also cause the bot to remove any further configuration entries it
has stored for this repository, such as the token.

Commands
--------

A complete overview of the commands.

=======  ===============================   ==========================================================
Command  Argument(s)                       Result
=======  ===============================   ==========================================================
route    <repository> <channel>            routes messages for <repository> to <channel>
route    <repository> <channel> <events>   routes messages for <repository> to <channel> for <events>
routes                                     show all repositories and routes
routes   <repository>                      show all routes for a repository
routes   <repository> <repository>         show all routes for multiple repositories
defaults                                   show the current defaults
defaults <events>                          what events should be routed by default
token    <repository> <token>              configure the token for a repository


Contributing
------------

This plugin is in its early stages but should be usable. However, since
there's a lot of different event types with different actions it might not be
able to gracefully deal with them all just yet and bugs may arise.

Right now we support:

  * pull_request
  * pull_request_review_comment
  * issues
  * push

Feel free to submit pull requests for new features and fixes or issues if you
encounter problems using this plugin.

License
-------

This code is licensed under the GPLv3, see the LICENSE file.
