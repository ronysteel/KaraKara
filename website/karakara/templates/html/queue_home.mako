<%inherit file="_base.mako"/>

<%doc>
  Developer Note:
    If you add any 'if' statements to this template, ensure you update the etag generator for the homepage
</%doc>

## Easter Egg for users who look at the code
<!--
    YOU WIN!
    --------
    Welcome iquisitive hax0r!
    Those who look at code deserve a treat.

    Navigate to '/settings' to look under the hood at the current settings.
    If you want to look futher then checkout the github repo
        http://github.com/calaldees/karakara/
    Send us a message, get involved, submit a feature request or contribute a new bugfix/feature yourself.

    Hint:
        If you buy the people running the event some snacks, sweets or drinks
        they may bypass the queue and slip a track in for you and a friend.
-->

## TODO - 'request.registry.settings' is depricated for queue level settings
<% disbaled_message = request.queue.settings.get('karakara.template.menu.disable') %>
% if not identity.get('admin', False) and disbaled_message:
    <p>${disbaled_message}</p>
% else:
    <% path_queue = paths['queue'] %>

    <a href="${path_queue}/search_tags/"   data-role="button">${_('mobile.home.search_tags')}</a>
    <a href="${path_queue}/queue_items"          data-role="button">${_('mobile.home.queue')}</a>

    % if identity.get('faves',[]):
    <a href="${path_queue}/fave"           data-role="button">${_('mobile.home.fave')}</a>
    % endif

    ## Disbaled until we can reimplement it as 'messaging'
    ##<a href="${path_queue}/feedback"       data-role="button">${_('mobile.home.feedback')}</a>
% endif

% if identity.get('admin', False):
    <p>ALL ADMIN LINKS ARE BROKEN AND WILL BE MOVED TO BOOTSTRAP/COMUNITY</p>
    <a href="/player/player.html" data-role="button" class="admin">${_('mobile.home.player')}</a>
    <a href="/track_list"         data-role="button" class="admin">${_('mobile.home.track_list')}</a>
    <a href="/settings"           data-role="button" class="admin">${_('mobile.home.settings')}</a>
    <a href="/static/form_badgenames.html" data-role="button" class="admin">${_('mobile.home.badgenames')}</a>
    <a href="/admin_lock"         data-role="button" class="admin">${_('mobile.home.admin_lock')}</a>
    <a href="/remote"             data-role="button" class="admin">${_('mobile.home.remote')}</a>
    <a href="/inject_testdata"    data-role="button" class="admin">${_('mobile.home.inject_testdata')}</a>
    <a href="/priority_tokens"    data-role="button" class="admin">${_('mobile.home.priority_tokens')}</a>
    <a href="/admin"              data-role="button" class="admin">${_('mobile.home.admin')}</a>
    <a href="/comunity"           data-role="button" class="admin">${_('mobile.home.comunity')}</a>
% endif
