Database Model Defination
=========================

.. _user:

User
----

============== ============== =============================================
Field          DataType       Remark
============== ============== =============================================
**id**         Text
name           Text           Name should be unique
password       Text           Generally password should be encoded
permission     BigInteger
expired        Boolean
last_login     DateTime       Last login time
create_time    DateTime
============== ============== =============================================

.. _category:

Category
--------

============== ============== =============================================
Field          DataType       Remark
============== ============== =============================================
**id**         Text
name           Text           The name should be unique
create_time    DateTime
create_by      Text           Foreign Key: :ref:`user`
============== ============== =============================================

.. _article:

Article
-------

============== ============== =============================================
Field          DataType       Remark
============== ============== =============================================
**id**         Text
is_commentable Boolean        True: the article can be commented
title          Text
text_type      Text           Decide render engine
text_source    Text
content        Text
read_count     Integer        Times to read article
post_time      DateTime
update_time    DateTime
public         Boolean        True: the article is only visible to its author
category       Text           Foreign Key: :ref:`category`
author         Text           Foreign Key: :ref:`user`
============== ============== =============================================

.. _comment:

Comment
-------

============== ============== =============================================
Field          DataType       Remark
============== ============== =============================================
content        Text
nickname       Text
reviewed       Boolean        True: every readers can see this comment
create_time    DateTime
ip_address     Text
article        Text           Foreign Key: :ref:`article`
user           Text           Foreign Key: :ref:`user`
refer_to       Text           Comment refers to. Foreign Key: :ref:`comment`
============== ============== =============================================

.. _event:

Event
-----

============== ============== =============================================
Field          DataType       Remark
============== ============== =============================================
type           Text
description    Text
ip_address     Text
endpoint       Text
request        Text           Reserve the request without body
create_time    DateTime
user           Text           Current user id. Foreign Key: :ref:`user`
============== ============== =============================================
