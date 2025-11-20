import unittest
from unittest.mock import MagicMock, patch
from glacierPy import lib
import botocore.exceptions

class TestGlacierPyLib(unittest.TestCase):

    @patch('glacierPy.lib.get_glacier_client')
    def test_get_vaults(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_vaults.return_value = {'VaultList': [{'VaultName': 'test-vault'}]}

        vaults = lib.get_vaults()
        self.assertEqual(vaults, [{'VaultName': 'test-vault'}])
        mock_client.list_vaults.assert_called_once()

    @patch('glacierPy.lib.get_glacier_client')
    def test_get_jobs(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_client.list_jobs.return_value = {'JobList': []}

        jobs = lib.get_jobs('test-vault')
        self.assertEqual(jobs, {'JobList': []})
        mock_client.list_jobs.assert_called_once_with(vaultName='test-vault')

    @patch('glacierPy.lib.get_glacier_client')
    def test_retrieve_inventory(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        lib.retrieve_inventory('test-vault')
        mock_client.initiate_job.assert_called_once()
        call_args = mock_client.initiate_job.call_args[1]
        self.assertEqual(call_args['vaultName'], 'test-vault')
        self.assertEqual(call_args['jobParameters']['Type'], 'inventory-retrieval')

    @patch('glacierPy.lib.get_glacier_client')
    def test_delete_vault_success(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        lib.delete_vault('test-vault')
        mock_client.delete_vault.assert_called_once_with(vaultName='test-vault')

    @patch('glacierPy.lib.get_glacier_client')
    def test_delete_vault_failure(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        
        # Create a mock exception
        error_response = {'Error': {'Code': 'InvalidParameterValueException', 'Message': 'Vault not empty'}}
        exception = botocore.exceptions.ClientError(error_response, 'DeleteVault')
        # We need to mock the exception class on the client object because the code catches client.exceptions.InvalidParameterValueException
        # However, botocore dynamic exceptions are tricky to mock exactly as they appear on the client.
        # A simpler approach for this specific test might be to mock the exception class itself if possible, 
        # or just verify the print output if we can't easily mock the dynamic exception class structure.
        
        # Let's try to mock the exception on the client instance
        mock_client.exceptions.InvalidParameterValueException = Exception 
        mock_client.delete_vault.side_effect = Exception()

        # Capture logging
        with patch('glacierPy.lib.logger') as mock_logger:
            lib.delete_vault('test-vault')
            # We expect a warning log
            self.assertTrue(mock_logger.warning.called)

if __name__ == '__main__':
    unittest.main()
