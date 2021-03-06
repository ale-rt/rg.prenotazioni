from Acquisition import aq_inner
from OFS.SimpleItem import SimpleItem
from zope.component import adapts
from zope.component.interfaces import ComponentLookupError
from zope.interface import Interface, implements
from zope.formlib import form
from zope import schema

from plone.app.contentrules.browser.formhelper import AddForm, EditForm
from plone.contentrules.rule.interfaces import IRuleElementData, IExecutable

from Products.CMFCore.utils import getToolByName
from rg.prenotazioni import prenotazioniMessageFactory as _


class IMovedPrenotazioneAction(Interface):
    """Definition of the configuration available for a mail action
    """

    subject = schema.TextLine(
        title=_(u"Subject"),
        description=_(u"Subject of the message"),
        required=True
        )

    source = schema.TextLine(
        title=_(u"Sender email"),
        description=_('source_help',
                      default=u"The email address that sends the email. If no email is "
                              u"provided here, it will use the address from portal."),
         required=False
         )

    message = schema.Text(
        title=_(u"Message"),
        description=_('message_help',
            default=u"Type in here the message that you want to mail. Some "
                    u"defined content can be replaced: ${title} will be replaced with booking title (user fullname). ${date} will be replaced with booking new date. ${url} will be replaced by the booking url. ${portal} will be replaced by the title "
                    u"of the portal."),
        required=True
        )


class MovedPrenotazioneAction(SimpleItem):
    """
    The implementation of the action defined before
    """
    implements(IMovedPrenotazioneAction, IRuleElementData)

    subject = u''
    source = u''
    message = u''

    element = 'rg.prenotazioni.actions.MovedPrenotazione'

    @property
    def summary(self):
        return _(u"Email report to prenotazione owner")


class MailActionExecutor(object):
    """
    The executor for this action.
    """
    implements(IExecutable)
    adapts(Interface, IMovedPrenotazioneAction, Interface)

    def __init__(self, context, element, event):
        self.context = context
        self.element = element
        self.event = event

    def __call__(self):
        mailhost = getToolByName(aq_inner(self.context), "MailHost")
        if not mailhost:
            raise ComponentLookupError('You must have a Mailhost utility to '
                                       'execute this action')
        source = self.element.source
        urltool = getToolByName(aq_inner(self.context), "portal_url")
        portal = urltool.getPortalObject()
        email_charset = portal.getProperty('email_charset')
        if not source:
            # no source provided, looking for the site wide from email
            # address
            from_address = portal.getProperty('email_from_address')
            if not from_address:
                raise ValueError('You must provide a source address for this '
                                 'action or enter an email in the portal properties')
            from_name = portal.getProperty('email_from_name')
            source = "%s <%s>" % (from_name, from_address)
        plone_view = portal.restrictedTraverse("@@plone")
        obj = self.event.object
        dest = obj.getEmail()
        message = self.element.message
        message = message.replace("${date}", plone_view.toLocalizedTime(obj.getData_prenotazione()))
        message = message.replace("${url}", obj.absolute_url())
        message = message.replace("${title}", obj.Title())
        message = message.replace("${portal}", portal.Title())
        subject = self.element.subject
        subject = subject.replace("${url}", obj.absolute_url())
        subject = subject.replace("${title}", obj.Title())
        subject = subject.replace("${portal}", portal.Title())

        self.context.plone_log('sending to: %s' % dest)
        try:
            # sending mail in Plone 4
            mailhost.send(message, mto=dest, mfrom=source,
                    subject=subject, charset=email_charset)
        except:
            #sending mail in Plone 3
            mailhost.secureSend(message, dest, source,
                    subject=subject, subtype='plain',
                    charset=email_charset, debug=False)

        return True


class MovedPrenotazioneAddForm(AddForm):
    """
    An add form for the mail action
    """
    form_fields = form.FormFields(IMovedPrenotazioneAction)
    label = _(u"Add moved booking Mail Action")
    description = _(u"A mail action that sends email notify when a booking is moved in an other slot.")
    form_name = _(u"Configure element")

    def create(self, data):
        a = MovedPrenotazioneAction()
        form.applyChanges(a, self.form_fields, data)
        return a


class MovedPrenotazioneEditForm(EditForm):
    """
    An edit form for the mail action
    """
    form_fields = form.FormFields(IMovedPrenotazioneAction)
    label = _(u"Edit moved booking Mail Action")
    description = _(u"A mail action that sends email notify when a booking is moved in an other slot.")
    form_name = _(u"Configure element")
