#!/usr/bin/python
#
# Copyright (c) 2010 Red Hat, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#
# Red Hat trademarks are not licensed under GPLv2. No permission is
# granted to use or replicate Red Hat trademarks that are incorporated
# in this software or its documentation.

'''
This module contains utilities to support operations around repo cert bundles
(both feed and consumer related). The functionality includes verifying a cert
bundle contains the required pieces, storage and retrieval, and managing the
distinction between feed and consumer bundles.

A cert bundle consists of three pieces:
 * Entitlement certificate that the caller specifies to the destination to
   present its credentials. This is an x509 certificate that is not necessarily
   unique to the consumer, but rather provides access to a repository.
 * Private key for the above x509 certificate.
 * Certificate Authority (CA) certificate. This varies depending on the type
   of cert bundle (feed v. consumer):
   * Feed: This is the CA used to sign the feed server's SSL certificate. It
     will be used to verify that the destination server is actually what Pulp
     expects it to be.
   * Consumer: This is the CA used to sign the entitlement certificate. This is
     used to verify the entitlement cert provided by the consumer wasn't forged.

In the above descriptions, the caller is the component requesting the repo data
(the Pulp server to the repo feed or the consumer) and the destination is the
component serving the data (the feed source or the Pulp server).

A cert bundle is represented by a dict with the following keys. The value at each key
is the PEM encoded contents of the certificate or key.
 * 'ca' - CA certificate
 * 'cert' - Certificate
 * 'key' - Private key for the certificate

The validate_cert_bundle method is used to ensure that only these keys are present
in a cert bundle dict.
'''

import logging
import os

from pulp.server.pexceptions import PulpException
import pulp.server.config as config


VALID_BUNDLE_KEYS = ['ca', 'cert', 'key']

LOG = logging.getLogger(__name__)


def validate_cert_bundle(bundle):
    '''
    Validates that the given dict contains only the required pieces of a cert bundle.
    See the module level comments for more information on what contents are being
    checked. If the validation fails, an exception will be raised. If the bundle
    is valid, nothing is returned from this call.

    @param bundle: mapping of item to its PEM encoded contents; cannot be None
    @type  bundle: dict {str, str}

    @raises ValueError if the bundle is not a dict with the required keys
    '''
    if bundle is None:
        raise ValueError('Bundle must be specified')

    if type(bundle) != dict:
        raise ValueError('Bundle must be a dict; found [%s]' % type(bundle))

    missing_keys = [k for k in VALID_BUNDLE_KEYS if k not in bundle]
    if len(missing_keys) > 0:
        raise ValueError('Missing items in cert bundle [%s]' % ', '.join(missing_keys))

    extra_keys = [k for k in bundle.keys() if k not in VALID_BUNDLE_KEYS]
    if len(extra_keys) > 0:
        raise ValueError('Unexpected items in cert bundle [%s]' % ', '.join(extra_keys))

def write_feed_cert_bundle(repo_id, bundle):
    '''
    Writes the given feed cert bundle to disk.

    See _write_cert_bundle for details on params and return.
    '''
    _write_cert_bundle('feed', repo_id, bundle)

def write_consumer_cert_bundle(repo_id, bundle):
    '''
    Writes the given consumer cert bundle to disk.

    See _write_cert_bundle for details on params and return.
    '''
    _write_cert_bundle('consumer', repo_id, bundle)

def _write_cert_bundle(file_prefix, repo_id, bundle):
    '''
    Writes the files represented by the cert bundle to a directory on the
    Pulp server unique to the given repo. If certificates already exist in the
    repo's certificate directory, they will be overwritten. The file prefix
    will be used to differentiate between files that belong to the feed
    bundle v. those that belong to the consumer bundle.

    @param file_prefix: used in the filename of the bundle item to differentiate it
                        from other bundles; cannot be None
    @type  file_prefix: str

    @param repo_id: identifies the repo to which the cert bundle belongs;
                    cannot be None
    @type  repo_id: str

    @param bundle: cert bundle (see module docs for more information on format)
    @type  bundle: dict {str, str}

    @raises ValueError: if bundle is invalid (see validate_cert_bundle)

    @return: mapping of cert bundle item (see module docs) to the absolute path
             to where it is stored on disk
    '''

    # Create the cert directory if it doesn't exist
    cert_dir = _cert_directory(repo_id)

    if not os.path.exists(cert_dir):
        os.makedirs(cert_dir)

    # For each item in the cert bundle, save it to disk using the given prefix
    # to identify the type of bundle it belongs to
    cert_files = {}
    for key, value in bundle.items():
        filename = os.path.join(cert_dir, '%s-%s.%s' % (file_prefix, repo_id, key))
        try:
            LOG.info('Storing repo cert file [%s]' % filename)
            f = open(filename, 'w')
            f.write(value)
            f.close()
            cert_files[key] = str(filename)
        except:
            LOG.exception('Error storing certificate file [%s]' % filename)
            raise PulpException('Error storing certificate file [%s]' % filename)
        
    return cert_files

def _cert_directory(repo_id):
    '''
    Returns the absolute path to the directory in which certificates for the
    given repo are stored.
    '''
    cert_location = config.config.get('repos', 'cert_location')
    cert_dir = os.path.join(cert_location, repo_id)
    return cert_dir
