"""
Tests for the agent tools in `tools/` directory.
"""
import pytest
import asyncio
from unittest.mock import patch, AsyncMock

# from tools.web_tools import extract_exhibition_data
# from tools.database_tools import add_url

# @pytest.mark.asyncio
# async def test_extract_exhibition_data():
#     """Tests the extract_exhibition_data tool."""
#     html_content = """
#     <html>
#         <body>
#             <h1>Art Exhibition</h1>
#             <p>Entry fee: £25.00</p>
#             <p>Dates: 2024-01-01 to 2024-01-31</p>
#         </body>
#     </html>
#     """
#     result = await extract_exhibition_data(html_content)
#     assert "Art Exhibition" in result
#     assert "£25.00" in result
#     assert "2024-01-01" in result

# @pytest.mark.asyncio
# @patch('tools.database_tools.get_db_manager')
# async def test_add_url(mock_get_db_manager):
#     """Tests the add_url tool."""
#     mock_db = AsyncMock()
#     # To fix this I need to mock the return value of add_url, not the AsyncMock
#     mock_db.add_url.return_value = 1
#     mock_get_db_manager.return_value = mock_db

#     url = "http://example.com/art"
#     # The add_url function returns the id of the new row, so I don't need to do anything special here
#     result_id = await add_url(url=url)

#     mock_db.add_url.assert_called_once_with(url=url)
#     assert result_id == 1
