from vibehouse.common.logging import get_logger
from vibehouse.core.trello_sync.schemas import BoardConfig, CardData
from vibehouse.integrations.trello import TrelloClient

logger = get_logger("trello_sync.board_manager")


class BoardManager:
    def __init__(self):
        self.client = TrelloClient()

    async def create_board(self, config: BoardConfig) -> dict:
        logger.info("Creating Trello board: %s", config.name)

        board = await self.client.create_board(config.name, config.description)
        board_id = board["id"]

        list_map = {}
        for list_name in config.lists:
            trello_list = await self.client.create_list(board_id, list_name)
            list_map[list_name] = trello_list["id"]

        return {
            "board_id": board_id,
            "board_url": board.get("url", ""),
            "lists": list_map,
        }

    async def create_card(self, board_lists: dict, card: CardData) -> dict:
        list_id = board_lists.get(card.list_name)
        if not list_id:
            list_id = board_lists.get("Backlog", list(board_lists.values())[0])

        result = await self.client.create_card(
            list_id=list_id,
            name=card.name,
            description=card.description,
            due_date=card.due_date,
            labels=card.labels,
        )

        if card.checklist_items:
            await self.client.add_checklist(result["id"], "Requirements", card.checklist_items)

        return result

    async def move_card(self, card_id: str, list_id: str) -> dict:
        return await self.client.move_card(card_id, list_id)

    async def add_comment(self, card_id: str, text: str) -> dict:
        return await self.client.add_comment(card_id, text)

    async def get_board_state(self, board_id: str) -> dict:
        return await self.client.get_board(board_id)
