from scripts.enrichment import service_client


def test_nonce_transaction_subphases_are_closed_safe_codes():
    for code in (
        'service_auth_nonce_transaction_unavailable',
        'service_auth_nonce_get_unavailable',
        'service_auth_nonce_put_unavailable',
        'service_auth_nonce_commit_unavailable',
        'service_auth_nonce_list_unavailable',
        'service_auth_nonce_delete_unavailable',
    ):
        assert service_client.classify_private_error(code) == code
