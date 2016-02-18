# coding: utf-8

import os
from StringIO import StringIO
from email.utils import COMMASPACE
from girlfriend.testing import GirlFriendTestCase
from girlfriend.plugin.mail import (
    SMTPManager,
    Attachment,
    SendMailPlugin,
    Mail,
)
from girlfriend.util.config import Config


class SMTPManagerTestCase(GirlFriendTestCase):

    def test_validate_config(self):
        smtp_manager = SMTPManager()
        config = Config({
            "smtp_test": {
                "host": "smtp.163.com",
                "account": "17600817832@163.com",
                "password": "gf123456"
            }
        })
        smtp_manager.validate_config(config)
        self.assertEquals(config["smtp_test"]["port"], 25)

        config["smtp_test"]["port"] = "25"
        smtp_manager = SMTPManager()
        smtp_manager.validate_config(config)
        self.assertEquals(config["smtp_test"]["port"], 25)


class AttachmentTestCase(GirlFriendTestCase):

    def test_build_mime_object(self):
        with open("test_attachment.txt", "w") as f:
            f.write("Hello! Hawaii!")

        # test file path
        attachment = Attachment("test_attachment.txt",
                                "text/plain", u"测试文本.txt".encode("utf-8"))
        mime_object = attachment.build_mime_object()

        # test file object
        attachment = Attachment(
            open("test_attachment.txt", "r"), "text/plain",
            u"测试文本.txt".encode("utf-8"))
        mime_object_2 = attachment.build_mime_object()
        self.assertEquals(mime_object.as_string(), mime_object_2.as_string())

        # test StringIO
        attachment = Attachment(
            StringIO("Hello! Hawaii!"), "text/plain",
            u"测试文本.txt".encode("utf-8"))
        mime_object_3 = attachment.build_mime_object()
        self.assertEquals(mime_object.as_string(), mime_object_3.as_string())

        os.remove("test_attachment.txt")


class SendMailPluginTestCase(GirlFriendTestCase):

    def setUp(self):
        self.config = Config({
            "smtp_test": {
                "host": "smtp.163.com",
                "port": 465,
                "account": "17600817832@163.com",
                "password": "gf123456",
                "ssl": "true"
            }
        })
        self.send_mail_plugin = SendMailPlugin()
        self.send_mail_plugin.config_validator(self.config)

    def test_execute(self):
        ctx = {}
        self.send_mail_plugin.execute(
            ctx,
            "test",
            receivers="17600817832@163.com",
            sender="17600817832@163.com",
            subject=u"新年快乐",
            content=u"新年快乐!"
        )

    def test_multi_receiver(self):
        ctx = {}
        self.send_mail_plugin.execute(
            ctx,
            "test",
            receivers=COMMASPACE.join([
                "17600817832@163.com",
                "chihz3800@163.com",
                "hongze.chi@gmail.com"
            ]),
            sender="17600817832@163.com",
            subject=lambda ctx, receiver: u"你好, " + receiver,
            content=lambda ctx, receiver: u"你好, " + receiver
        )

        self.send_mail_plugin.execute(
            ctx,
            "test",
            receivers=[
                "hongze.chi@gmail.com",
                "chihz3800@163.com",
            ],
            sender="17600817832@163.com",
            subject=lambda ctx, receiver: u"Hahaha, " + receiver,
            content=lambda ctx, receiver: u"你好, content " + receiver,
            attachments=[
                Attachment(StringIO("simple!"),
                           "text/plain", u"文本.txt".encode("gb2312")),
                Attachment(StringIO("naive!"),
                           "text/plain", u"文本2.txt".encode("gb2312"))
            ]
        )

    def test_customize(self):

        class MyMail(Mail):

            def __init__(self, context, receiver):
                super(MyMail, self).__init__(context, receiver)

            @property
            def sender(self):
                return "17600817832@163.com"

            @property
            def receiver_email(self):
                return self._receiver.email

            @property
            def subject(self):
                return u"新年快乐"

            @property
            def content(self):
                return u"新年快乐，发大财！{}".format(self._receiver.name)

            @property
            def attachments(self):
                return [
                    Attachment(StringIO("simple!"),
                               "text/plain", u"文本.txt".encode("gb2312")),
                    Attachment(StringIO("naive!"),
                               "text/plain", u"文本2.txt".encode("gb2312"))
                ]

        class User(object):

            def __init__(self, name, email):
                self.name = name
                self.email = email

        ctx = {}
        self.send_mail_plugin.execute(
            ctx,
            "test",
            receivers=[
                User(u"迟宏泽", "h.ongzechi@gmail.com"),
                User(u"小白", "hongze.chi@gmail.com")
            ],
            mail=MyMail
        )
