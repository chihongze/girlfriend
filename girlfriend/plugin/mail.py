# coding: utf-8

"""邮件发送相关插件
"""

import types
import smtplib
import os.path
from abc import (
    ABCMeta,
    abstractproperty,
)
from functools import partial
from email import encoders
from email.Header import Header
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from girlfriend.util.lang import args2fields
from girlfriend.exception import InvalidArgumentException
from girlfriend.util.validating import Rule


class SMTPManager(object):
    """管理配置文件中所有登记的SMTP服务信息"""

    config_rules = (
        # SMTP 主机地址
        Rule("host", type=types.StringTypes, required=True),
        # SMTP 端口号
        Rule("port", type=(types.StringTypes, int), required=False,
             regex=r"^\d+$", default=25),
        # SMTP 账号
        Rule("account", type=types.StringTypes, required=True),
        # SMTP 密码
        Rule("password", type=types.StringTypes, required=True),
        # 是否使用SSL通道发送
        Rule("ssl", type=types.StringTypes, required=False,
             regex=r"^(true|false)$", default="false")
    )

    def __init__(self):
        self._all_smtp_config = {}
        self._validated = False  # 尚未进行验证

    def validate_config(self, config):
        """验证配置，并将配置添加到容器之中"""
        if self._validated:
            return
        for section in config.prefix("smtp_"):
            smtp_config_items = config[section]
            for rule in SMTPManager.config_rules:
                item_value = smtp_config_items.get(rule.name)
                rule.validate(item_value)
                if item_value is None:
                    smtp_config_items[rule.name] = rule.default
                if rule.name == "port" and isinstance(
                        item_value, types.StringTypes):
                    smtp_config_items["port"] = int(item_value)
            smtp_config = SMTPConfig(**smtp_config_items)
            self._all_smtp_config[section] = smtp_config
        self._validated = True

    def get_smtp_config(self, smtp_server_name):
        return self._all_smtp_config[smtp_server_name]


class SMTPConfig(object):
    """SMTP配置信息"""

    @args2fields()
    def __init__(self, host, port, account, password, ssl):
        pass
        self._ssl = (ssl.lower() == "true")

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def account(self):
        return self._account

    @property
    def password(self):
        return self._password

    @property
    def ssl(self):
        return self._ssl


_smtp_manager = SMTPManager()


class SendMailPlugin(object):

    """邮件发送插件，支持附件和模板渲染
       使用方法如下：

       Job(
          "send_mail",
          args = {
              "server": "test_smtp"
              "sender": "sam@gf.com",
              "receiver": "$users",
              "subject": subject_generator,
              "content": content_generator,
              "encoding": "utf-8",
              "attachments": (
                  Attachment(...),
                  Attachment(...),
                  Attachment(...)
              )
          }
       )

       或者：

       Job(
          "send_mail",
          args = {
              "server": "test_smtp"
              "receiver": "$users",
              "mail": TestMail
          }
       )
    """

    name = "send_mail"

    @staticmethod
    def config_validator(config):
        global _smtp_manager
        _smtp_manager.validate_config(config)

    def execute(self, context, server, receivers, mail=None,
                sender=None, subject=None, content=None,
                encoding="utf-8", attachments=None):
        """
        :param server SMTP服务名称
        :param receiver 收件人列表，可以是字符串组成的邮箱列表，也可以是对象列表
        :param mail  用来动态表述邮件内容的邮件类
        :param sender 发件人，可以传递字符串或函数，函数接受上下文以及收件人对象作为参数
        :param subject 标题，可传递字符串或函数，函数参数同上
        :param content 正文，可以是字符串或函数，函数参数同上
        :param encoding 编码，可以是字符串或函数，函数参数同上
        :param attachments 附件列表，可以是Attachment对象列表或者函数，函数参数同上
        """

        # 组装Mail对象列表
        mail_list = []
        if mail is not None:
            if not issubclass(mail, Mail):
                raise InvalidArgumentException(
                    u"mail参数必须是girlfriend.plugin.mail.Mail类型的子类")
        else:
            mail = partial(_Mail, sender=sender, subject=subject,
                           content=content, encoding=encoding,
                           attachments=attachments)

        if isinstance(receivers, types.StringTypes):
            mail_list = [mail(context=context, receiver=receivers)]
        else:
            mail_list = [mail(context=context, receiver=receiver)
                         for receiver in receivers]

        # 创建SMTP连接
        smtp_config = _smtp_manager.get_smtp_config("smtp_" + server)
        if smtp_config.ssl:
            smtp_server = smtplib.SMTP_SSL(
                host=smtp_config.host,
                port=smtp_config.port
            )
        else:
            smtp_server = smtplib.SMTP(
                host=smtp_config.host,
                port=smtp_config.port
            )
        smtp_server.login(smtp_config.account, smtp_config.password)

        try:
            for mail in mail_list:
                msg = MIMEMultipart()
                msg['From'] = mail.sender
                msg['To'] = mail.receiver_email
                msg['Subject'] = Header(mail.subject, mail.encoding)
                msg.attach(MIMEText(mail.content, "html", mail.encoding))
                attachments = mail.attachments
                if attachments:
                    for attachment in attachments:
                        msg.attach(attachment.build_mime_object())
                smtp_server.sendmail(
                    mail.sender,
                    [email_address.strip()
                     for email_address in mail.receiver_email.split(",")],
                    msg.as_string())
        finally:
            smtp_server.quit()


class Mail(object):

    __metaclass__ = ABCMeta

    def __init__(self, context, receiver):
        self._context = context
        self._receiver = receiver

    @abstractproperty
    def sender(self):
        """发件人地址"""
        pass

    @abstractproperty
    def receiver_email(self):
        """收件人邮箱地址"""
        pass

    @abstractproperty
    def subject(self):
        """邮件标题"""
        pass

    @abstractproperty
    def content(self):
        """邮件正文"""
        pass

    @property
    def attachments(self):
        """邮件附件"""
        return []

    @property
    def encoding(self):
        """编码，默认为UTF-8，如果你家Boss或PM喜欢用Mac装Windows，那么可以覆盖为gb2312"""
        return "utf-8"


class _Mail(Mail):

    """内置的Mail实现"""

    def __init__(self, context, receiver, sender, subject,
                 content, encoding, attachments):
        super(_Mail, self).__init__(context, receiver)
        self._sender = sender
        self._subject = subject
        self._content = content
        self._encoding = encoding
        self._attachments = attachments

    def _get_value(self, value):
        if isinstance(value, types.FunctionType):
            return value(self._context, self._receiver)
        return value

    @property
    def sender(self):
        return self._get_value(self._sender)

    @property
    def receiver_email(self):
        return self._get_value(self._receiver)

    @property
    def subject(self):
        return self._get_value(self._subject)

    @property
    def content(self):
        return self._get_value(self._content)

    @property
    def attachments(self):
        return self._get_value(self._attachments)

    @property
    def encoding(self):
        return self._get_value(self._encoding)


class Attachment(object):

    """附件"""

    @args2fields()
    def __init__(self, attachment_file, mime_type, attachment_filename=None):
        """
        :param attachment_file  作为附件的文件对象，可以是file对象或者StringIO对象，
                                如果是字符串，那么将作为文件路径进行加载
        :param mime_type  附件的mime type，比如application/octet-stream
        :param attachment_filename  附件所使用的文件名
        """
        if attachment_filename is None:
            if isinstance(attachment_file, types.StringTypes):
                self._attachment_filename = os.path.split(
                    attachment_file)[1]
            elif isinstance(attachment_file, types.FileType):
                self._attachment_filename = os.path.split(
                    attachment_file.name)[1]
            else:
                raise InvalidArgumentException(
                    u"必须制定attachement_filename参数作为附件文件名")

    def build_mime_object(self):
        """构建Mime对象"""
        mime_type = self._mime_type.split("/")
        mime = MIMEBase(mime_type[0], mime_type[1])
        mime.set_payload(self._gen_payload())
        encoders.encode_base64(mime)
        mime.add_header(
            'Content-Disposition',
            'attachment; filename="{}"'.format(self._attachment_filename))
        return mime

    def _gen_payload(self):
        # 文件类型的情况
        if isinstance(self._attachment_file, types.FileType):
            try:
                return self._attachment_file.read()
            finally:
                self._attachment_file.close()
        # 字符串路径的情况
        elif isinstance(self._attachment_file, types.StringTypes):
            with open(self._attachment_file, "r") as f:
                return f.read()
        # StringIO or cStringIO
        else:
            self._attachment_file.seek(0)
            return self._attachment_file.read()
