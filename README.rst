##########
RepoHook
##########

RepoHook is a webhook endpoint for Err_ as well as a set of commands to
configure the routing of messages to chatrooms.

This plugin does not depend on anything but Err_ itself and the Python
standard library.

The supported Python versions are:

* Python 2.7.7+
* Python 3.3+

Python versions prior to 2.7 aren't supported by Err_ and Python versions
prior to Python 2.7.7 miss the ``hmac.compare_digest`` method to securely
and in constant time compare two digests. This is needed to validate
incoming requests as coming from Github or GitLab. Other web VCS providers
can be easily added in the future, we encourage you to submit a PR if your
favorite website supports webhooks.

Webhooks
--------

Webhooks are a way for websites, or really any service, to notify another
service that something happened. Github/GitLab provide webhooks that based on
an event send a payload over HTTP to another service which can then react
accordingly.

They enable near real-time notifications of actions, so if someone pushes
code to a repository Github/GitLab will send a HTTP payload with some
information about that event.

This mechanism can be used to receive almost instantaneous notifications of
activity that happens on a repository on Github/GitLab. It's a great way
to hook up your repository to Err_.

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

Note: GitLab token validation is currently not supported.

Installation
------------

To be able to use webhooks with Err_ you'll need to configure its
built-in webserver first using the ``!webserver`` command once you've loaded
the webserver plugin.

We **strongly** advise you to not expose the webserver plugin directly to
the internet but instead put it behind a proxying nginx or Apache HTTPD
and let those handle terminating SSL traffic for you and passing the
request on to Err_'s webserver.

The webhook on Github/GitLab needs to be configured to send a payload to
https://your-endoint.tld/repohook with a *Content type* of
``application/json``.

In order to install this plugin all you need to do is:

.. code-block:: text

   !repos install https://github.com/daenney/err-repohook.git

Configuration
-------------

Most Err_ plugins can be configured using the ``!config PluginName`` action.
However, since this plugin has to handle fairly complex configuration
separate commands were created for you to set everything up and interact
with this plugin's settings.

To view the full configuration of the plugin you can issue the following:

.. code-block:: text

   !repohook config

There is no way to manipulate the configuration through this command, only
view it. Since its output contains sensitive data, like the tokens, it is
restricted to users with administrative privileges.

nginx
^^^^^

An example of nginx plus the webserver plugin:

.. code-block:: text

   !load Webserver
   !config Webserver {'HOST': '127.0.0.1', 'PORT': 3141}
   !reload RepoHook

The nginx configured to handle https://your-endpoint.tld and proxy all
requests to Err_:

.. code-block:: nginx

   server {
       listen 443 ssl;
       server_name your-endpoint.tld;

       ssl_certificate /path/to/certificate.crt;
       ssl_certificate_key /path/to/certificate.key;

       root /tmp;

       location / {
           proxy_set_header  Host $host;
           proxy_set_header  X-Real-IP $remote_addr;
           proxy_set_header  X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header  X-Forwarded-Proto $scheme;
           proxy_hide_header Server;
           proxy_pass http://127.0.0.1:3141;
       }
   }

Environment variables
^^^^^^^^^^^^^^^^^^^^^

If you run the bot through an init system make sure the following variables
are set correctly or the plugin won't load (on Python 3, 2 seems fine):

.. code-block:: bash

   export LC_ALL=en_US.UTF-8
   export LANG=en_US.UTF-8
   export LANGUAGE=en_US.UTF-8

Feel free to substitute ``en_US`` for something else but make sure you use
the UTF-8 variants.

circus
~~~~~~

This is all that's needed for Circus_:

.. code-block:: ini

   [env:watcher_name]
   LC_ALL=en_US.UTF-8
   LANG=en_US.UTF-8
   LANGUAGE=en_US.UTF-8

Usage
-----

route
^^^^^

The ``route`` command is the first to be executed when adding a new repository
for which events will be forwarded. It takes as arguments the repository
and the channel you want messages routed to:

.. code-block:: text

   !repohook route example/example example@example.com

By default we will forward the following types of events to that channel:

* An issue is opened/closed/changed
* Someone comments on an issue
* Someone comments on a commit
* Code is pushed
* A pull request is raised
* A review is left on a change in a pull request

You can also pass in which events should be routed at creation time:

.. code-block:: text

   !repohook route example/example example@example.com push issues comment

Changing these events later simply requires you to call this command again.
Omitting the events when a route already exists resets the route to the
default events.

routes
^^^^^^

In order to list all the routes for a repository:

.. code-block:: text

   !repohook routes example/example

You can pass multiple repositories to ``!repohook routes`` by separating them
with a space. In return you'll get the route configuration for every of those
repositories.

.. code-block:: text

   !repohook routes example/example test/test

If you want to list all routes simply call the command with no arguments:

.. code-block:: text

   !repohook routes

default events
^^^^^^^^^^^^^^

The default events to subscribe on can be altered:

.. code-block:: text

   !repohook defaults push commit issues pull_request

Changing the default will only affect new routes, existing ones will have
to be updated manually using the ``route`` command.

Issuing that same command without any events will list the currently active
defaults:

.. code-block:: text

   !repohook defaults

token
^^^^^

Once you've added a route you need to configure the token for the repository.
This token is used for all routes of this repository and only needs to be set
up once.

We **strongly** advise you to do this in a private session with the bot that is
not being logged anywhere so your token doesn't accidentally show up in
places it shouldn't.

.. code-block:: text

   !repohook token example/example TOKEN

It is not possible to request the token once it is set. If you believe it
was set incorrectly, simply set it again to what it should be.

As explained in the above Security section, setting a token and configuring it
on the webhook is required for events to be validated and routed.

remove
^^^^^^

In order to remove a route issue the following:

.. code-block:: text

   !repohook remove example/example example@example.com

If this is the last route we know about for that repository any further
configuration entries for that repository will be removed too, like the
token.

Should you wish to remove all routes, essentially removing the repository:

.. code-block:: text

   !repohook remove example/example

This will also cause the bot to remove any further configuration entries it
has stored for this repository, such as the token.

Commands
--------

A complete overview of the commands.

+----------+---------------------------------+----------------------------------------------------------------------+
| Command  | Arugment(s)                     | Result                                                               |
+==========+=================================+======================================================================+
| help     |                                 | show usage information                                               |
+----------+---------------------------------+----------------------------------------------------------------------+
| route    | <repository> <channel>          | relay messages for <repository> to <channel>                         |
+----------+---------------------------------+----------------------------------------------------------------------+
| route    | <repository> <channel> <events> | relay messages triggered by <events> from <repository> to <channel>  |
+----------+---------------------------------+----------------------------------------------------------------------+
| routes   |                                 | show all repositories and routes                                     |
+----------+---------------------------------+----------------------------------------------------------------------+
| routes   | <repository>                    | show all routes for <repository>                                     |
+----------+---------------------------------+----------------------------------------------------------------------+
| routes   | <repository> <repository>       | show all routes for multiple <repository>'s                          |
+----------+---------------------------------+----------------------------------------------------------------------+
| defaults |                                 | show all current defaults                                            |
+----------+---------------------------------+----------------------------------------------------------------------+
| defaults | <events>                        | what events should be relayed by default                             |
+----------+---------------------------------+----------------------------------------------------------------------+
| token    | <repository> <token>            | configure the token for the repository to validate incoming messages |
+----------+---------------------------------+----------------------------------------------------------------------+


Contributing
------------

This plugin is in its early stages but should be usable. However, since
there's a lot of different event types with different actions it might not be
able to gracefully deal with them all just yet and bugs may arise.

Right now we support:

* ``pull_request``
* ``pull_request_review_comment``
* ``issues``
* ``issue_comment``
* ``commit_comment``
* ``push``

Feel free to submit pull requests for new features and fixes or issues if you
encounter problems using this plugin.

License
-------

This code is licensed under the GPLv3, see the LICENSE file.

.. _Err: http://errbot.net
.. _Securing your webhooks: https://developer.github.com/webhooks/securing
.. _Circus: http://circus.readthedocs.org
