import datetime
import time
import copy

from mailpile.crypto.keydata import get_keydata
from mailpile.i18n import gettext
from mailpile.plugins import PluginManager
from mailpile.plugins.keylookup import LookupHandler
from mailpile.plugins.keylookup import register_crypto_key_lookup_handler
from mailpile.plugins.search import Search
from mailpile.mailutils.emails import Email


_ = lambda t: t
_plugins = PluginManager(builtin=__file__)


GLOBAL_KEY_CACHE = {}


def _PRUNE_GLOBAL_KEY_CACHE():
    global GLOBAL_KEY_CACHE
    for k in GLOBAL_KEY_CACHE.keys()[10:]:
        del GLOBAL_KEY_CACHE[k]


PGP_KEY_SUFFIXES = ('pub', 'asc', 'key', 'pgp')

def _might_be_pgp_key(filename, mimetype):
    filename = (filename or '').lower()
    return ((mimetype == "application/pgp-keys") or
            (filename.lower().split('.')[-1] in PGP_KEY_SUFFIXES and
             'encrypted' not in filename and
             'signature' not in filename))

class EmailKeyLookupHandler(LookupHandler, Search):
    NAME = _("E-mail keys")
    PRIORITY = 5
    TIMEOUT = 25  # 5 seconds per message we are willing to parse
    LOCAL = True

    def __init__(self, session, *args, **kwargs):
        LookupHandler.__init__(self, session, *args, **kwargs)
        Search.__init__(self, session)

        global GLOBAL_KEY_CACHE
        self.key_cache = GLOBAL_KEY_CACHE
        _PRUNE_GLOBAL_KEY_CACHE()

    def _score(self, key):
        return (1, _('Found key in local e-mail'))

    def _lookup(self, address, strict_email_match=False):
        results = {}
        address = address.lower()
        terms = ['from:%s' % address, 'has:pgpkey', '+pgpkey:%s' % address]
        session, idx = self._do_search(search=terms)
        deadline = time.time() + (0.75 * self.TIMEOUT)
        for messageid in session.results[:5]:
            for key_info, raw_key in self._get_message_keys(messageid):
                if strict_email_match:
                    match = [u for u in key_info.get('uids', [])
                             if (u['email'] or '').lower() == address]
                    if not match:
                        continue
                fp = key_info["fingerprint"]
                results[fp] = copy.copy(key_info)
                self.key_cache[fp] = raw_key
            if len(results) > 5 or time.time() > deadline:
                break
        return results

    def _getkey(self, keydata):
        data = self.key_cache.get(keydata["fingerprint"])
        if data:
            return self._gnupg().import_keys(data)
        else:
            raise ValueError("Key not found")

    def _get_message_keys(self, messageid):
        keys = self.key_cache.get(messageid, [])
        if not keys:
            email = Email(self._idx(), messageid)
            attachments = email.get_message_tree(want=["attachments"]
                                                 )["attachments"]
            for part in attachments:
                if _might_be_pgp_key(part["filename"], part["mimetype"]):
                    key = part["part"].get_payload(None, True)
                    for keydata in get_keydata(key):
                        keys.append((keydata, key))
                    if len(keys) > 5:  # Just to set some limit...
                        break
            self.key_cache[messageid] = keys
        return keys


def has_pgpkey_data_kw_extractor(index, msg, mimetype, filename, part, loader,
                                 body_info=None, **kwargs):
    kws = []
    if _might_be_pgp_key(filename, mimetype):
        data = get_keydata(part.get_payload(None, True))
        for keydata in data:
            for uid in keydata.get('uids', []):
                if uid.get('email'):
                    kws.append('%s:pgpkey' % uid['email'].lower())
        if data:
            body_info['pgp_key'] = filename
            kws += ['pgpkey:has']

    # FIXME: If this is a PGP key, make all the key IDs searchable so
    #        we can find this file again later! Searching by e-mail is lame.
    #        This is issue #655 ?

    return kws


register_crypto_key_lookup_handler(EmailKeyLookupHandler)
_plugins.register_data_kw_extractor('pgpkey', has_pgpkey_data_kw_extractor)
_ = gettext
