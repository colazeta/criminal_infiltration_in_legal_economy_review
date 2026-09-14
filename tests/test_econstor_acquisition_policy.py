"""EconStor acquisition expansion is exact-host and repository-scoped."""
import unittest

from scripts.oa_acquisition import authorised_host


class EconStorAcquisitionPolicyTests(unittest.TestCase):
    def test_econstor_is_authorised_only_on_exact_https_host(self):
        self.assertEqual(
            authorised_host('https://www.econstor.eu/bitstream/10419/216340/1/dp13028.pdf'),
            'repository',
        )
        for url in (
            'http://www.econstor.eu/bitstream/10419/216340/1/dp13028.pdf',
            'https://econstor.eu/bitstream/10419/216340/1/dp13028.pdf',
            'https://www.econstor.eu.evil.test/paper.pdf',
        ):
            with self.assertRaises(ValueError):
                authorised_host(url)


if __name__ == '__main__':
    unittest.main()
