from errbot.templating import tenv


GITHUB_EVENTS = ['commit_comment', 'create', 'delete', 'deployment',
                 'deployment_status', 'fork', 'gollum', 'issue_comment',
                 'issues', 'member', 'page_build', 'public',
                 'pull_request_review_comment', 'pull_request', 'push',
                 'release', 'status', 'team_add', 'watch', '*']
GITLAB_EVENTS = ['push_hook', 'tag_push_hook', 'issue_hook', 'note_hook', 'merge_request_hook']
SUPPORTED_EVENTS = GITHUB_EVENTS + GITLAB_EVENTS
DEFAULT_EVENTS = ['commit_comment', 'issue_comment', 'issues', 'pull_request_review_comment',
                  'pull_request', 'push', 'push_hook', 'tag_push_hook', 'issue_hook',
                  'note_hook', 'merge_request_hook']


class CommonGitWebProvider(object):
    def create_message(self, body, event_type, repo):
        """
        Dispatch the message. Check explicitly with hasattr first. When
        using a try/catch with AttributeError errors in the
        message_function which result in an AttributeError would cause
        us to call msg_generic, which is not what we want.
        """
        message_function = 'msg_{0}'.format(event_type)
        if hasattr(self, message_function):
            message = getattr(self, message_function)(body, repo)
        else:
            message = self.msg_generic(body, repo, event_type)
        return message


class GithubHandlers(CommonGitWebProvider):
    name = 'Github'

    def get_repo(self, body):
        return body['repository']['full_name']

    def msg_generic(self, body, repo, event_type):
        return tenv().get_template('generic.html').render(locals().copy())

    def msg_issues(self, body, repo):
        action = body['action']
        number = body['issue']['number']
        title = body['issue']['title']
        user = body['issue']['user']['login']
        url = body['issue']['url']
        is_assigned = body['issue']['assignee']
        if is_assigned is not None:
            assignee = body['issue']['assignee']['login']

        return tenv().get_template('issues.html').render(locals().copy())

    def msg_pull_request(self, body, repo):
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

    def msg_pull_request_review_comment(self, body, repo):
        action = body['action']
        user = body['comment']['user']['login']
        line = body['comment']['position']
        l_url = body['comment']['html_url']
        pr = body['pull_request']['number']
        url = body['pull_request']['html_url']
        if action == 'created':
            action = 'commented'
        return tenv().get_template('pull_request_review_comment.html').render(locals().copy())

    def msg_push(self, body, repo):
        user = body['pusher']['name']
        commits = len(body['commits'])
        branch = body['ref'].split('/')[-1]
        url = body['compare']
        return tenv().get_template('push.html').render(locals().copy())

    def msg_status(*args):
        """Status events are crazy and free form. There's no sane, consistent
        or logical way to deal with them."""
        return None

    def msg_issue_comment(self, body, repo):
        action = body['action']
        user = body['comment']['user']['login']
        number = body['issue']['number']
        title = body['issue']['title']
        url = body['issue']['html_url']
        if action == 'created':
            action = 'commented'
        return tenv().get_template('issue_comment.html').render(locals().copy())

    def msg_commit_comment(self, body, repo):
        user = body['comment']['user']['login']
        url = body['comment']['html_url']
        line = body['comment']['line']
        sha = body['comment']['commit_id']
        return tenv().get_template('commit_comment.html').render(locals().copy())


class GitLabHandlers(CommonGitWebProvider):
    name = 'GitLab'

    def get_repo(self, body):
        return body['project']['name']

    def map_event_type(self, event_type):
        return {
            'push_hook': 'push',
            'issue_hook': 'issue',
            'note_hook': 'commit_comment',
        }.get(event_type)

    def create_message(self, body, event_type, repo):
        mapped_event_type = self.map_event_type(event_type)
        return super(GitLabHandlers, self).create_message(body, mapped_event_type, repo)

    def msg_generic(self, body, repo, event_type):
        return tenv().get_template('generic.html').render(locals().copy())

    def msg_push(self, body, repo):
        user = body['user_name']
        commits = len(body['commits'])
        branch = '/'.join(body['ref'].split('/')[2:])
        url = body['commits'][-1]['url'] if commits else body['project']['web_url']
        return tenv().get_template('push.html').render(locals().copy())

    def msg_commit_comment(self, body, repo):
        user = body['user']['name']
        url = body['object_attributes']['url']
        line = body['object_attributes']['note']
        sha = body['object_attributes']['commit_id']
        return tenv().get_template('commit_comment.html').render(locals().copy())
