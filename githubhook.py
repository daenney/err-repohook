# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import hashlib
import hmac
import json
import logging

from errbot import BotPlugin, botcmd, webhook, holder
from errbot.templating import tenv
from config import BOT_PREFIX, CHATROOM_FN
from bottle import abort

log = logging.getLogger(name='errbot.plugins.GithubHook')

GITHUB_EVENTS = ['commit_comment', 'create', 'delete', 'deployment',
                 'deployment_status', 'fork', 'gollum', 'issue_comment',
                 'issues', 'member', 'page_build', 'public',
                 'pull_request_review_comment', 'pull_request', 'push',
                 'release', 'status', 'team_add', 'watch', '*']

DEFAULT_EVENTS = ['commit_comment', 'issue_comment', 'issues',
                  'pull_request_review_comment', 'pull_request', 'push']

DEFAULT_CONFIG = { 'default_events': DEFAULT_EVENTS, 'repositories': {}, }

REQUIRED_HEADERS = ['X-Hub-Signature', 'X-Github-Event']

HELP_MSG = ('Please see the output of `{0}github help` for usage '
            'and configuration instructions.'.format(BOT_PREFIX))

REPO_UNKNOWN = 'The repository {0} is unknown to me.'
EVENT_UNKNOWN = 'Unknown event {0}, skipping.'


class GithubHook(BotPlugin):

    min_err_version = '2.1.0'

    def get_configuration_template(self):
        return HELP_MSG

    def check_configuration(self, configuration):
        pass

    def configure(self, configuration):
        if configuration is not None:
            config = configuration
        else:
            config = DEFAULT_CONFIG
        super(GithubHook, self).configure(config)

    #################################################################
    # Convenience methods to get, check or set configuration options.
    #################################################################

    def clear_repo(self, repo):
        """Completely remove a repository's configuration."""
        if self.has_repo(repo):
            self.config['repositories'].pop(repo)
            self.save_config()

    def clear_route(self, repo, room):
        """Remove a route from a repository."""
        if self.has_route(repo, room):
            self.config['repositories'][repo]['routes'].pop(room)
            self.save_config()

    def has_repo(self, repo):
        """Check if the repository is known."""
        if self.get_repo(repo) is None:
            return False
        else:
            return True

    def has_route(self, repo, room):
        """Check if we have a route for this repository to that room."""
        if self.get_route(repo, room) is None:
            return False
        else:
            return True

    def get_defaults(self):
        """Return the default events that get relayed."""
        return self.config['default_events']

    def get_events(self, repo, room):
        """Return all the events being relayed for this combination of
        repository and room, aka a route.
        """
        return self.config['repositories'].get(repo, {}) \
                                          .get('routes', {}) \
                                          .get(room, {}) \
                                          .get('events')

    def get_repo(self, repo):
        """Return the repo's configuration or None."""
        return self.config['repositories'].get(repo)

    def get_repos(self):
        """Return a list of all repositories we have configured."""
        return self.config['repositories'].keys()

    def get_route(self, repo, room):
        """Return the configuration of this route."""
        return self.config['repositories'].get(repo, {}) \
                                          .get('routes', {}) \
                                          .get(room)

    def get_routes(self, repo):
        """Fetch the routes for a repository.
        Always check if the repository exists before calling this.
        """
        return self.config['repositories'].get(repo, {}) \
                                          .get('routes', {}) \
                                          .keys()

    def get_token(self, repo):
        """Returns the token for a repository.

        Be **very** careful as to where you call this as this returns the
        plain text, uncensored token.
        """
        return self.config['repositories'].get(repo, {}).get('token')

    def set_defaults(self, defaults):
        """Set which events are relayed by default."""
        self.config['default_events'] = defaults
        self.save_config()

    def set_events(self, repo, room, events):
        """Set the events to be relayed for this combination of repository
        and room."""
        self.config['repositories'][repo]['routes'][room]['events'] = events
        self.save_config()

    def set_route(self, repo, room):
        """Create a configuration entry for this route.

        If the repository is unknown to us, add the repository first.
        """
        if self.get_repo(repo) is None:
            self.config['repositories'][repo] = { 'routes': {}, 'token': None }
        self.config['repositories'][repo]['routes'][room] = {}
        self.save_config()

    def set_token(self, repo, token):
        """Set the token for a repository."""
        self.config['repositories'][repo]['token'] = token
        self.save_config()

    def save_config(self):
        """Save the current configuration.

        This method takes care of saving the configuration since we can't
        use !config GithubHook <configuration blob> to configure this
        plugin.
        """
        holder.bot.set_plugin_configuration('GithubHook', self.config)

    def show_repo_config(self, repo):
        """Builds up a complete list of rooms and events for a repository."""
        if self.has_repo(repo):
            message = ['Routing {0} to:'.format(repo)]
            for room in self.get_routes(repo):
                message.append(' • {0} for events: {1}'.format(room, ' '.join(self.get_events(repo, room))))
            return '\n'.join(message)
        else:
            return REPO_UNKNOWN.format(repo)

    ###########################################################
    # Commands for the user to get, set or clear configuration.
    ###########################################################

    @botcmd
    def github(self, *args):
        """Github root command, return usage information."""
        return self.github_help()

    @botcmd
    def github_help(self, *args):
        """Output help."""
        message = []
        message.append('This plugin has multiple commands: ')
        message.append(' • config: to display the full configuration of '
                       'this plugin (not human friendly)')
        message.append(' • route <repo> <room>: to relay messages from '
                       '<repo> to <room> for events '
                       '{0}'.format(' '.join(self.get_defaults())))
        message.append(' • route <repo> <room> <events>: to relay '
                       'messages from <repo> to <room> for <events>')
        message.append(' • routes <repo>: show routes for this repository')
        message.append(' • routes: to display all routes')
        message.append(' • defaults <events>: to configure the events we '
                       'should forward by default')
        message.append(' • defaults: to show the events to be forwarded '
                       'by default')
        message.append(' • token <repo>: to configure the repository '
                       'secret')
        message.append('Please see https://github.com/daenney/err-githubhook'
                       '/blob/master/README.rst for more information.')
        return '\n'.join(message)

    @botcmd(admin_only=True)
    def github_config(self, *args):
        """Returns the current configuration of the plugin."""
        # pprint can't deal with nested dicts, json.dumps is aces.
        return json.dumps(self.config, indent=4, sort_keys=True)

    @botcmd(admin_only=True)
    def github_reset(self, *args):
        """Nuke the complete configuration."""
        self.config = DEFAULT_CONFIG
        self.save_config()
        return 'Done. All configuration has been expunged.'

    @botcmd(split_args_with=None)
    def github_defaults(self, message, args):
        """Get or set what events are relayed by default for new routes."""
        if args:
            events = []
            for event in args:
                if event in GITHUB_EVENTS:
                    events.append(event)
                else:
                    yield EVENT_UNKNOWN.format(event)
            self.set_defaults(events)
            yield ('Done. Newly created routes will default to '
                   'receiving: {0}.'.format(' '.join(events)))
        else:
            yield ('Events routed by default: '
                   '{0}.'.format(' '.join(self.get_defaults())))

    @botcmd(split_args_with=None)
    def github_route(self, message, args):
        """Map a repository to a chatroom, essentially creating a route.

        This takes two or three arguments: author/repo, a chatroom and
        optionally a list of events.

        If you do not specify a list of events the route will default to
        receiving the events configured as 'default_events'.
        """
        if len(args) >= 2:
            repo = args[0]
            room = args[1]
            # Slicing on an index that, potentially, doesn't exist returns
            # an empty list instead of raising an IndexError
            events = args[2:]

            if not self.has_route(repo, room):
                self.set_route(repo, room)

            if events:
                for event in events[:]:
                    if event not in GITHUB_EVENTS:
                        events.remove(event)
                        yield EVENT_UNKNOWN.format(event)
            else:
                events = self.get_defaults()
            self.set_events(repo, room, events)
            yield ('Done. Relaying messages from {0} to {1} for '
                   'events: {2}'.format(repo, room, ' '.join(events)))
        else:
            yield HELP_MSG

    @botcmd(split_args_with=None)
    def github_routes(self, message, args):
        """Displays the routes for one, multiple or all repositories."""
        if args:
            for repo in args:
                if self.has_repo(repo):
                    yield self.show_repo_config(repo)
                else:
                    yield REPO_UNKNOWN.format(repo)
        else:
            repos = self.get_repos()
            if repos:
                yield ("You asked for it, here are all the repositories, the "
                       "rooms and associated events that are relayed:")
                for repo in repos:
                    yield self.show_repo_config(repo)
            else:
                yield 'No repositories configured, nothing to show.'

    @botcmd(split_args_with=None)
    def github_token(self, message, args):
        """Register the secret token for a repository.

        This token is needed to validate the incoming request as coming from
        Github. It must be configured on your repository's webhook settings
        too.
        """
        if len(args) != 2:
            return HELP_MSG
        else:
            repo = args[0]
            token = args[1]
            if self.has_repo(repo):
                self.set_token(repo, token)
                return 'Token set for {0}.'.format(repo)
            else:
                return REPO_UNKNOWN.format(repo)

    @botcmd(split_args_with=None)
    def github_remove(self, message, args):
        """Remove a route or a repository.

        If only one argument is passed all configuration for that repository
        is removed.

        When two arguments are passed that specific route is removed. If this
        was the last route any remaining configuration for the repository is
        removed too. With only one route remaining this essentially achieves
        the same result as calling this with only the repository as argument.
        """
        if len(args) == 1:
            repo = args[0]
            self.clear_repo(repo)
            yield 'Removed all configuration for {0}.'.format(repo)
        elif len(args) == 2:
            repo = args[0]
            room = args[1]
            self.clear_route(repo, room)
            yield 'Removed route for {0} to {1}.'.format(repo, room)
            if not self.get_routes(repo):
                self.clear_repo(repo)
                yield ('No more routes for {0}, removing remaining '
                       'configuration.'.format(repo))
        else:
            yield HELP_MSG

    @webhook(r'/github', methods=('POST',), raw=True)
    def receive(self, request):
        """Handle the incoming payload.

        Here be dragons.

        Validate the payload as best as we can and then delegate the creation
        of a sensible message to a function specific to this event. If no such
        function exists, use a generic message function.

        Once we have a message, route it to the appropriate channels.
        """

        if not self.validate_incoming(request):
            abort(400)

        event_type = request.get_header('X-Github-Event').lower()
        signature = request.get_header('X-Hub-Signature')
        body = request.json

        if event_type == 'ping':
            log.info('Received ping event triggered by {0}'.format(body['hook']['url']))
            return None

        repo = body['repository']['full_name']

        if self.get_repo(repo) is None:
            # Not a repository we know so accept the payload, return 200 but
            # discard the message
            log.info('Message received for {0} but no such repository '
                      'is configured'.format(repo))
            return None

        token = self.get_token(repo)
        if token is None:
            # No token, no validation. Accept the payload since it's not their
            # fault that the user hasn't configured a token yet but log a
            # message about it and discard it.
            log.info('Message received for {0} but no token '
                     'configured'.format(repo))
            return None

        if not self.valid_message(request.body, token, signature):
            ip = request.get_header('X-Real-IP')
            if ip is None:
                log.warn('Event received for {0} but could not validate it.'.format(repo))
            else:
                log.warn('Event received for {0} from {1} but could not validate it.'.format(repo, ip))
            abort(403)

        # Dispatch the message. Check explicitly with hasattr first. When
        # using a try/catch with AttributeError errors in the
        # message_function which result in an AttributeError would cause
        # us to call msg_generic, which is not what we want.
        message_function = 'msg_{0}'.format(event_type)
        if hasattr(self, message_function):
                message = getattr(self, message_function)(body, repo)
        else:
            message = self.msg_generic(body, repo, event_type)

        # - if we have a message and is it not empty or None
        # - get all rooms for the repository we received the event for
        # - check if we should deliver this event
        # - join the room (this won't do anything if we're already joined)
        # - send the message
        if message and message is not None:
            for room in self.get_routes(repo):
                events = self.get_events(repo, room)
                if event_type in events or '*' in events:
                    self.join_room(room, username=CHATROOM_FN)
                    self.send(room, message, message_type='groupchat')

    @staticmethod
    def validate_incoming(request):
        """Validate the incoming request:

          * Check if the headers we need exist
          * Check if the payload decodes to something we expect
          * Check if it contains the repository
        """

        if request.content_type != 'application/json':
            return False
        for header in REQUIRED_HEADERS:
            if request.get_header(header) is None:
                return False

        try:
            body = request.json
        except ValueError:
            return False

        if not isinstance(body, dict):
            return False

        return True

    @staticmethod
    def valid_message(message, token, signature):
        """Validate the signature of the incoming payload.

        The header received from Github is in the form of algorithm=hash.
        """
        if signature is None:
            return False

        alg, sig = signature.split('=')
        if alg != 'sha1':
            return False

        mac = hmac.new(token.encode(), msg=message.read(), digestmod=hashlib.sha1).hexdigest()
        return hmac.compare_digest(mac, sig)

    @staticmethod
    def msg_generic(body, repo, event_type):
        return tenv().get_template('generic.html').render(locals().copy())

    @staticmethod
    def msg_issues(body, repo):
        action = body['action']
        number = body['issue']['number']
        title = body['issue']['title']
        user = body['issue']['user']['login']
        url = body['issue']['url']
        is_assigned = body['issue']['assignee']
        if is_assigned is not None:
            assignee = body['issue']['assignee']['login']

        return tenv().get_template('issues.html').render(locals().copy())

    @staticmethod
    def msg_pull_request(body, repo):
        action = body['action']
        number = body['pull_request']['number']
        user = body['pull_request']['user']['login']
        url = body['pull_request']['html_url']
        merged = body['pull_request']['merged']
        if action == 'closed' and merged:
            user = body['pull_request']['merged_by']['login']
            action = 'merged'
        if action == 'synchronize':
            action = 'updated'
        return tenv().get_template('pull_request.html').render(locals().copy())

    @staticmethod
    def msg_pull_request_review_comment(body, repo):
        action = body['action']
        user = body['comment']['user']['login']
        line = body['comment']['position']
        l_url = body['comment']['html_url']
        pr = body['pull_request']['number']
        url = body['pull_request']['html_url']
        if action == 'created':
            action = 'commented'
        return tenv().get_template('pull_request_review_comment.html').render(locals().copy())

    @staticmethod
    def msg_push(body, repo):
        user = body['pusher']['name']
        commits = len(body['commits'])
        branch = body['ref'].split('/')[-1]
        url = body['compare']
        return tenv().get_template('push.html').render(locals().copy())

    @staticmethod
    def msg_status(*args):
        """Status events are crazy and free form. There's no sane, consistent
        or logical way to deal with them."""
        return None


    @staticmethod
    def msg_issue_comment(body, repo):
        action = body['action']
        user = body['comment']['user']['login']
        number = body['issue']['number']
        title = body['issue']['title']
        url = body['issue']['html_url']
        if action == 'created':
            action = 'commented'
        return tenv().get_template('issue_comment.html').render(locals().copy())
