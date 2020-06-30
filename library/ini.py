# This file is a part of the USBIPManager software
# library/ini.py
# Implements interfaces for interacting with software and daemons configurations
#
# Copyright (c) 2018-2019 Mikhail Antonov
# Repository: https://github.com/lompal/USBIPManager
# TODO Change documentation URL
# Documentation: https://gthb.in/blog/post/2019/9/5/34-usbip-manager-software-and-servers-configurations-api-reference

from library import config, performance

from os import remove
from collections import namedtuple
from configparser import ConfigParser


class InsertError(Exception):
    """ Error inserting a daemon """
    pass


class RemoveError(Exception):
    """ Error removing a daemon """
    pass


class Base(metaclass=config.Singleton):
    """ Base class for software/daemon manager """
    def __init__(self, base, config_filename):
        self._base = base
        self._config_filename = config_filename

        self._encoding = 'utf-8'

        self._config = self._get_config()

        self._get = None
        self._getint = None
        self._getfloat = None
        self._getboolean = None

        self._config_param = namedtuple('config_param', 'type value')

        # Default configuration options for daemons and software
        # KEY - configuration option name
        # VALUE - tuple with option type and option default value
        self._dmn_param = {
            'dmn_port': self._config_param(str, '3240'),
            'dmn_name': self._config_param(str, ''),
            'dmn_filter': self._config_param(str, ''),
            'ssh': self._config_param(bool, 'False'),
            'ssh_port': self._config_param(int, '22'),
            'ssh_usr': self._config_param(str, 'pi'),
            'ssh_pwd': self._config_param(str, 'raspberry'),
            'hub': self._config_param(bool, 'False'),
            'hub_cfg_utl': self._config_param(str, 'uhubctl'),
            'hub_cfg': self._config_param(str, 'DUB-H7'),
            'hub_cfg_tmo': self._config_param(float, '3'),
            'sniffer': self._config_param(bool, 'False')
        }
        self._sw_param = {
            'lang': self._config_param(str, 'English'),
            'clt_ver': self._config_param(str, 'cezanne'),
            # TODO Store IP addresses as integers to avoid additional conversions
            'find_ip_ini': self._config_param(str, '192.168.80.10'),
            'find_ip_end': self._config_param(str, '192.168.80.100'),
            'dmn_def_port': self._config_param(int, '3240'),
            'dev_atch_tmo': self._config_param(float, '5'),
            'dev_dtch_tmo': self._config_param(float, '2.5'),
            'queue_tmo': self._config_param(float, '0.5'),
            'dmn_perf': self._config_param(bool, 'True'),
            'dmn_perf_tmo': self._config_param(float, '0.5'),
            'dmn_perf_sock_tmo': self._config_param(float, '0.1'),
            'dev_perf': self._config_param(bool, 'True'),
            'dev_perf_tmo': self._config_param(float, '0.5'),
            'sys_perf': self._config_param(bool, 'True'),
            'sys_perf_tmo': self._config_param(float, '0.5'),
            'net_perf': self._config_param(bool, 'True'),
            'net_perf_tmo': self._config_param(float, '0.25'),
            'net_perf_len': self._config_param(int, '151'),
            'net_perf_out_cl': self._config_param(str, 'Green'),
            'net_perf_out_wd': self._config_param(int, '2'),
            'net_perf_inc_cl': self._config_param(str, 'Red'),
            'net_perf_inc_wd': self._config_param(int, '2')
        }

        # Generate functions for getting configuration parameters by a template depending on the value data type
        self._actions = ('get', 'getint', 'getfloat', 'getboolean')
        for action in self._actions:
            setattr(self, f'_{action}', self._get_action(action))

    def _get_config(self):
        """ Read a specific configuration """
        _config = ConfigParser()
        _config.read([self._config_filename], encoding=self._encoding)
        return _config

    def _get_action(self, action):
        """ Function template for configuration instance """
        def _template(section, option):
            """ Get configuration parameter depending on the value data type """
            if self._config.has_option(section, option):
                # TODO Default value with warning message if ValueError exception occurs
                return getattr(self._config, action)(section, option)
            return None
        return _template

    def _instance(self, instance):
        """ Switch-case for daemon and software configuration parameters depending on the value data type """
        return {
            str: self._get,
            int: self._getint,
            float: self._getfloat,
            bool: self._getboolean
        }.get(instance, self._get)

    def _attr_generator(self, class_obj, config_param):
        """ Generate setter and getter attributes for each default configuration option """
        for param in config_param:
            _type = config_param[param].type
            _fn = self._instance(_type)
            setattr(class_obj, param, property(
                lambda __self, __fn=_fn, __param=param: __fn(__self.section, __param),
                lambda __self, __value, __param=param: self._set(__self.section, **{__param: __value}))
            )

    def _set(self, section, **kwargs):
        """ Set the value of the configuration parameter """
        for option in kwargs:
            self._config.set(section, option, str(kwargs[option]))

    def write(self):
        """ Write an updated configuration file """
        remove(self._config_filename)
        with open(self._config_filename, 'a', encoding=self._encoding) as fp:
            self._config.write(fp)
        _perf = performance.Manager(self._base)
        _perf.reload()


class Daemon(Base, metaclass=config.Singleton):
    """ Daemon configuration manager """
    def __init__(self, base, ip_addr, config_filename='config.ini'):
        super().__init__(base, config_filename)
        self.section = ip_addr

        self._attr_generator(Daemon, self._dmn_param)


class DaemonManage(Base, metaclass=config.Singleton):
    """ Daemon configuration manager """
    def __init__(self, base, config_filename='config.ini'):
        super().__init__(base, config_filename)

    def _find(self, ip_addr):
        """ Search for a specific daemon by its IP address """
        if ip_addr in self._config.sections():
            return True
        return False

    def get_all(self):
        """ Retrieve a list of all daemons """
        _daemon = list()
        for section in self._config.sections():
            if section != 'SETTINGS':
                _daemon.append(section)
        return _daemon

    def load(self, ip_addr):
        """ Load a daemon by its IP address and create the necessary parameters """
        if self._find(ip_addr):
            raise InsertError
        self._config.add_section(ip_addr)
        for param in self._dmn_param:
            self._config.set(ip_addr, param, self._dmn_param[param].value)
        self.write()

    def remove(self, ip_addr):
        """ Delete the daemon by its IP address and all its parameters """
        if not self._find(ip_addr):
            raise RemoveError
        self._config.remove_section(ip_addr)
        self.write()


class SWConfig(Base, metaclass=config.Singleton):
    """ Software configuration manager """
    def __init__(self, base, config_filename='config.ini'):
        super().__init__(base, config_filename)
        self.section = 'SETTINGS'

        self._attr_generator(SWConfig, self._sw_param)


class CapturingConfig(Base, metaclass=config.Singleton):
    """ Change data capture settings - single instance """
    def __init__(self, base, ip_addr, config_filename='capturing.ini'):
        super().__init__(base, config_filename)
        self.section = ip_addr
