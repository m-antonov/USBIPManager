# This file is a part of the USBIPManager software
# library/validation.py
# Implements procedures for verification of required input fields
#
# Copyright (c) 2018-2019 Mikhail Antonov
# Repository: https://github.com/lompal/USBIPManager
# Documentation: XXX

from functools import partial
from ipaddress import ip_address
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
from PyQt5.QtWidgets import QLineEdit, QComboBox, QGroupBox, QCheckBox

# IP address input field regular expression and validator
_regex = '(?:[0-1]?[0-9]?[0-9]|2[0-4][0-9]|25[0-5])'
_pattern = QRegExp('^' + _regex + '\\.' + _regex + '\\.' + _regex + '\\.' + _regex + '$')
ip_validator = QRegExpValidator(_pattern)

# Form input validation stylesheets
_css = 'QLineEdit { background-color: %s }'
error_css = _css % '#f6989d'
success_css = _css % '#c4df9b'
warning_css = _css % '#fff79a'


def form_empty(form_req):
    """ Check required input fields for missing data """
    _form_req = tuple(filter(lambda __obj: not __obj.text(), form_req))
    return tuple(filter(lambda __obj: not __obj.setStyleSheet(error_css), _form_req))


def _valid_ip(value):
    """ Validate IP address """
    try:
        ip_address(value)
    except ValueError:
        return value


def form_valid(form_ip):
    """ Check required input fields for valid IP address """
    _form_ip = tuple(filter(lambda __obj: _valid_ip(__obj.text()), form_ip))
    return tuple(filter(lambda __obj: not __obj.setStyleSheet(error_css), _form_ip))


def _update_form(form):
    """  """
    if not form.text():
        return form.setStyleSheet(error_css)
    return form.setStyleSheet(success_css)


def _form_getter(form):
    """ Form value getter interface for different types of forms """
    if isinstance(form, QLineEdit):
        return form.text()

    if isinstance(form, QComboBox):
        return form.currentText()

    if isinstance(form, (QGroupBox, QCheckBox)):
        return form.isChecked()


class InterfaceManager:
    """  """
    def __init__(self, parent):
        self._parent = parent

        self._form_changelog = {}

    def _toggle(self, condition):
        """  """
        for form in self._parent.sender().findChildren(QLineEdit):
            if condition:
                form.textChanged.emit(form.text())
                continue
            form.setStyleSheet('')

    def setup(self):
        """  """
        # TODO QLineEdit form int/float validation

        for form in self._parent.form_req:
            _form_value = getattr(self._parent.config, form.objectName())

            if isinstance(form, QComboBox):
                form.setCurrentText(str(_form_value))
                self._form_changelog[form] = str(_form_value)
                # TODO Message after changing a language
                continue

            if isinstance(form, QLineEdit):
                form.textChanged.connect(partial(_update_form, form))
                form.setText(str(_form_value))
                self._form_changelog[form] = str(_form_value)
                continue

            if isinstance(form, QGroupBox):
                for _object in form.findChildren(QLineEdit):
                    _object_value = str(getattr(self._parent.config, _object.objectName()))

                    _object.textChanged.connect(partial(_update_form, _object))
                    _object.setText(_object_value)
                    self._form_changelog[_object] = _object_value

                form.toggled.connect(partial(self._toggle))
                form.setChecked(_form_value)
                self._form_changelog[form] = _form_value
                # Force signal emitting to toggle unchecked group boxes
                form.toggled.emit(form.isChecked())

                for _object in form.findChildren(QComboBox):
                    _object_value = getattr(self._parent.config, _object.objectName())
                    _object.setCurrentText(_object_value)
                    self._form_changelog[_object] = _object_value

    def apply(self):
        """  """
        for form in self._form_changelog:
            _value = _form_getter(form)
            if self._form_changelog[form] != _value:
                if form.styleSheet() != error_css:
                    setattr(self._parent.config, form.objectName(), _value)
                    continue
                return
        self._parent.config.write()
        self._parent.close()
