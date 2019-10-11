# -*- coding:utf-8 -*-
from __future__ import unicode_literals

from limpyd import fields
from limpyd.exceptions import ImplementationError
from ..model import TestRedisModel, BaseModelTest, Email


class HashFieldTest(BaseModelTest):

    model = Email

    def test_hashfield_can_be_set_at_init(self):
        headers = {
            'from': 'foo@bar.com',
            'to': 'me@world.org'
        }
        obj = self.model(headers=headers)
        self.assertEqual(obj.headers.hget('from'), 'foo@bar.com')
        self.assertEqual(obj.headers.hget('to'), 'me@world.org')
        self.assertEqual(obj.headers.hstrlen('from'), 11)
        self.assertEqual(obj.headers.hstrlen('to'), 12)

    def test_hmset_should_set_values(self):
        obj = self.model()
        headers = {
            'from': 'foo@bar.com',
            'to': 'me@world.org'
        }
        obj.headers.hmset(**headers)
        self.assertEqual(obj.headers.hget('from'), 'foo@bar.com')
        self.assertEqual(obj.headers.hget('to'), 'me@world.org')

    def test_hmset_should_be_indexable(self):
        obj = self.model()
        headers = {
            'from': 'foo@bar.com',
            'to': 'me@world.org'
        }
        obj.headers.hmset(**headers)
        self.assertCollection([obj._pk], headers__from='foo@bar.com')
        self.assertCollection([obj._pk], headers__to='me@world.org')

        # Now change value and check old has been deindexed and new reindexed
        obj.headers.hmset(**{'from': 'you@mars.io'})
        self.assertCollection([], headers__from='you@moon.io')
        self.assertCollection([obj._pk], headers__from='you@mars.io')

    def test_hset_should_set_value_and_be_indexable(self):
        obj = self.model()
        obj.headers.hset('from', 'someone@cassini.io')
        self.assertEqual(obj.headers.hget('from'), 'someone@cassini.io')

        self.assertCollection([obj._pk], headers__from='someone@cassini.io')

        # Now change value and check old has been deindexed and new reindexed
        obj.headers.hset('from', 'someoneelse@cassini.io')
        self.assertCollection([], headers__from='someone@cassini.io')
        self.assertCollection([obj._pk], headers__from='someoneelse@cassini.io')

    def test_hincrby_should_set_value_and_be_indexable(self):
        obj = self.model()
        obj.headers.hincrby('Message-ID', 1)
        self.assertEqual(obj.headers.hget('Message-ID'), '1')
        self.assertCollection([obj._pk], **{'headers__Message-ID': '1'})
        # Now change value and check first has been deindexed and new redindexed
        obj.headers.hincrby('Message-ID', 1)
        self.assertEqual(obj.headers.hget('Message-ID'), '2')
        self.assertCollection([], **{'headers__Message-ID': '1'})
        self.assertCollection([obj._pk], **{'headers__Message-ID': '2'})

    def test_delete_hashfield(self):
        obj = self.model()
        headers = {
            'from': 'foo@bar.com',
            'to': 'me@world.org'
        }
        obj.headers.hmset(**headers)
        self.assertEqual(obj.headers.hget('from'), 'foo@bar.com')
        self.assertEqual(obj.headers.hget('to'), 'me@world.org')
        count = obj.headers.hdel('from', 'cc')  # try to delete "cc", a non-existing entry
        self.assertEqual(count, 1)
        self.assertEqual(obj.headers.hget('from'), None)
        self.assertCollection([], headers__from='foo@bar.com')
        self.assertCollection([obj._pk], headers__to='me@world.org')

        # Do not raise if we try to del a key that does not exist
        # (follow redis usage)
        obj.headers.hdel('a key that does not exist')

    def test_delete_whole_hashfield(self):
        obj = self.model()
        headers = {
            'from': 'foo@bar.com',
            'to': 'me@world.org'
        }
        obj.headers.hmset(**headers)

        obj.headers.delete()
        self.assertEqual(obj.headers.hgetall(), {})

    def test_hsetnx_should_index_only_if_value_is_new(self):
        obj = self.model()
        obj.headers.hset('to', 'two@three.org')
        with self.assertNumCommands(2 + self.COUNT_LOCK_COMMANDS):
            # one for setting value
            # one for indexing
            # + n for the lock
            obj.headers.hsetnx('from', 'one@two.org')

        # Chech value has been changed
        self.assertEqual(obj.headers.hget('from'), 'one@two.org')

        with self.assertNumCommands(1 + self.COUNT_LOCK_COMMANDS):
            # one for hsetnx, which should not set
            # none for indexing, the value didn't hange
            # + n for the lock
            obj.headers.hsetnx('from', 'three@four.org')

        # Chech value has not been changed
        self.assertEqual(obj.headers.hget('from'), 'one@two.org')

    def test_hgetall_should_return_a_dict(self):
        obj = self.model()
        headers = {
            'from': 'foo@bar.com',
            'to': 'me@world.org'
        }
        obj.headers.hmset(**headers)
        self.assertEqual(
            obj.headers.hgetall(),
            headers
        )

    def test_hmget_should_return_requested_values(self):
        headers = {
            'from': 'foo@bar.com',
            'to': 'me@world.org',
            'cc': 'someone@else.org',
        }
        obj = self.model(headers=headers)
        self.assertEqual(
            obj.headers.hmget('to', 'from'),
            ['me@world.org', 'foo@bar.com']
        )

    def test_hkeys_should_return_all_keys(self):
        headers = {
            'from': 'foo@bar.com',
            'to': 'me@world.org',
        }
        obj = self.model(headers=headers)
        self.assertEqual(
            set(obj.headers.hkeys()),
            {'from', 'to'}
        )

    def test_hvals_should_return_all_values(self):
        headers = {
            'from': 'foo@bar.com',
            'to': 'me@world.org',
        }
        obj = self.model(headers=headers)
        self.assertEqual(
            set(obj.headers.hvals()),
            {'foo@bar.com', 'me@world.org'}
        )

    def test_hexists_should_check_if_key_exists(self):
        headers = {
            'from': 'foo@bar.com',
            'to': 'me@world.org',
        }
        obj = self.model(headers=headers)
        self.assertEqual(obj.headers.hexists('from'), True)
        self.assertEqual(obj.headers.hexists('to'), True)
        self.assertEqual(obj.headers.hexists('cc'), False)

    def test_hlen_should_return_number_of_keys(self):
        headers = {
            'from': 'foo@bar.com',
            'to': 'me@world.org',
        }
        obj = self.model()
        self.assertEqual(obj.headers.hlen(), 0)
        obj.headers.hmset(**headers)
        self.assertEqual(obj.headers.hlen(), 2)

    def test_hashfields_cannot_be_unique(self):
        with self.assertRaises(ImplementationError):
            class TestUniquenessHashField(TestRedisModel):
                data = fields.HashField(indexable=True, unique=True)

    def test_hscan_should_scan_hash_keys(self):
        headers = {
            'from': 'foo@bar.com',
            'to': 'me@world.org'
        }
        obj = self.model(headers=headers)

        self.assertDictEqual(dict(obj.headers.hscan()), {
            'from': 'foo@bar.com',
            'to': 'me@world.org'
        })

        self.assertDictEqual(dict(obj.headers.hscan('fr*')), {
            'from': 'foo@bar.com',
        })
