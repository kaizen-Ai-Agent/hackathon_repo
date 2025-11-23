from ibm_watsonx_ai import ApiClient, ModelInference
from app.core.config import settings


class AIService:
    def __init__(self):
        self.client = ApiClient(apikey=settings.WATSONX_APIKEY, instance_url=settings.WATSONX_URL)
        self.model = ModelInference(self.client)
        self.model_name = 'ibm/granite-13b-instruct-v2'


async def generate_summary_for_meeting(self, meeting_id: str) -> str:
    # load transcript chunks from DB, coalesce
    from app.db.prisma_client import prisma
    chunks = await prisma.transcript.find_many(where={"meetingId": meeting_id}, order={'timestamp': 'asc'})