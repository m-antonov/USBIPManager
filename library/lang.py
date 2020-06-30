# This file is a part of the USBIPManager software
# library/lang.py
# Implements localized translation of messages beyond of PyQt5 objects
#
# Copyright (c) 2018-2019 Mikhail Antonov
# Repository: https://github.com/lompal/USBIPManager
# Documentation: XXX

from gettext import gettext as _


class USBIPManagerUI:
    """ Software main window interface """
    PopupScrollPoweroff = _('Poweroff all')
    PopupScrollLoad = _('Load daemon')
    PopupScrollClear = _('Clear all')
    PopupLogClear = _('Clear')
    MessageCloseTitle = _('Warning')
    MessageCloseText = _('Are you sure want to exit? All established connections will be terminated!')
    MessageCloseOK = _('OK')
    MessageCloseCancel = _('Cancel')
    AtchSeparator = _('Attach all')
    DtchSeparator = _('Detach all')
    PoolEmpty = _('Search pool is empty, use the search button and try again')


class LangSelfSearchUI:
    """ Modal window with automatic look for a USBIP daemon in a network by a given IP range """
    PopupCheck = _('Check all')
    PopupUncheck = _('Uncheck all')


class LangConfig:
    """ Software and daemons configuration interface """
    InsertError = _('IP address is already in the configuration - skipped')
    RemoveError = _('')


class LangFormValidation:
    """ Input fields validation """
    FormEmptyError = _('Highlighted fields are required')
    FormValidError = _('Invalid IP address')
    FormGTError = _('Incorrect search range')


class QueueManager:
    """ Queue manager """
    DebugExec = _('Executing background process')
    DebugCallback = _('Done background process')


class Performance:
    """ Performance measure """
    SystemCPU = _('CPU')
    SystemMEM = _('MEM')
    NetworkGraphIncoming = _('Incoming')
    NetworkGraphOutgoing = _('Outgoing')
    PopupReload = _('Reload')


class LangDaemon:
    """ USBIP daemon widget """
    LogSeparator = _('Daemon manager for')
    PopupPoweroff = _('Poweroff')
    PopupReload = _('Reload')
    PopupUnload = _('Unload')
    SearchExec = _('Performing search')
    SearchOffline = _('Daemon is offline')
    CheckUnstable = _('Connection is unstable')


class Tree:
    """ Daemon device bandwidth """
    ParamBaud = _('Baud')
    ParamNA = _('N/A')
    SnifferLoad = _('Load sniffer')
    SnifferUnload = _('Unload sniffer')
    SnifferReload = _('Reload sniffer')


class USBTop:
    """  """
    LogSeparator = _('USBTOP processing for')
    RunSuccess = _('USBTOP processing is running successfully')
    RunQuery = _('An error has occurred while executing a command over SSH')
    CancelSuccess = _('USBTOP processing has cancelled successfully')
    CancelError = _('Unable to cancel the USBTOP processing')
    AforeRun = _('USBTOP processing is already running')
    AforeCancel = _('USBTOP processing already cancelled or not running yet')
    EnableRequired = _('USBTOP processing is disabled or not configured yet - check your software configuration')


class SSH:
    """  """
    LogSeparator = _('SSH connection for')
    ActionGlobalHeading = _('Global SSH action')
    ActionGlobalOpen = _('Open SSH')
    ActionGlobalClose = _('Close SSH')
    ActionLocalHeading = _('Local SSH action')
    ActionLocalExec = _('Exec')
    NoValidConnectionsError = _('Unable to connect - check your daemon address and default port configuration')
    AuthenticationException = _('Authentication error - check your daemon username and password configuration')
    OpenSuccess = _('Connection has established successfully')
    CloseSuccess = _('Connection has closed successfully')
    CloseError = _('Unable to close the SSH connection')
    AforeOpen = _('Connection already opened')
    AforeClose = _('Connection already closed or not opened yet')
    ConnectionRequired = _('An active SSH connection to the daemon is required - connecting ...')
    EnableRequired = _('Connection is disabled or not configured yet - check your daemon SSH configuration')


class USB:
    """  """
    LogSeparator = _('USB recharging for')
    ActionGlobalHeading = _('Global USB action')
    ActionGlobalRecharge = _('Recharge entire USB hub')
    ActionLocalHeading = _('Local USB action')
    ActionLocalRecharge = _('Recharge')
    RechargeSuccess = _('USB device has recharged successfully')
    RechargeError = _('An error has occurred while recharging - check your hub configuration')
    RechargeCancel = _('Recharging has cancelled')
    RechargeQuery = _('An error has occurred while executing a command over SSH')


class USBIP:
    """  """
    LogSeparator = _('USBIP device from')
    ActionGlobalHeading = _('Global USBIP action')
    ActionGlobalAtch = _('Attach entire USBIP daemon')
    ActionGlobalDtch = _('Detach entire USBIP daemon')
    ActionLocalHeading = _('Local USBIP action')
    ActionLocalAtch = _('Attach')
    ActionLocalDtch = _('Detach')
    ExtraInformation = _('Getting an extra logical device configuration from the daemon')
    ExtraSuccess = _('An extra logical device configuration has got successfully')
    ExtraError = _('An error has occurred while getting an extra logical device configuration')
    ExtraCancel = _('Getting an extra logical device configuration has cancelled')
    ExtraQuery = _('An error has occurred while executing a command over SSH')
    AforeAtch = _('Device already attached')
    AforeDtch = _('Device already detached or not attached yet')
