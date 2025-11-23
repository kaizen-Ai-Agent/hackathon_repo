import logging
from datetime import datetime, timezone

from app.db.prisma_client import db # async Prisma client
from app.services.distributed_lock import DistributedLock
from app.services.ai_service import AIService

# Initialize AI service (IBM watsonx.ai)

ai_service = AIService()

async def meeting_wrapup_task(meeting_id: str):
    """
    Task executed by the scheduler when a meeting ends.
    Performs distributed locking, generates AI summary, stops meeting, updates DB.
    """
    lock = DistributedLock(f"lock:wrapup:{meeting_id}")
    if not await lock.acquire():
        logging.info(f"Wrap-up job for meeting {meeting_id} is locked by another worker. Skipping.")
        return

    try:  
        logging.info(f"Starting wrap-up for meeting {meeting_id}")  

        # Fetch meeting details  
        meeting = await db.meeting.find_unique(where={"id": meeting_id})  
        if not meeting:  
            logging.warning(f"Meeting {meeting_id} not found. Exiting wrap-up.")  
            return  

        if not meeting.isActive:  
            logging.info(f"Meeting {meeting_id} already closed.")  
            return  

        # 1. Stop recording / retrieve final transcripts  
        # (Assume recording stopped externally via Google API webhook or scheduler)  

        # 2. Generate AI summary  
        transcript_chunks = await db.transcript.find_many(where={"meetingId": meeting_id})  
        transcript_text = "\n".join([chunk.content for chunk in transcript_chunks])  

        if transcript_text.strip():  
            summary_content = await ai_service.generate_summary(meeting_id, transcript_text)  
            # Save summary to DB  
            await db.summary.upsert(  
                where={"meetingId": meeting_id},  
                create={"meetingId": meeting_id, "content": summary_content, "modelUsed": ai_service.model_name},  
                update={"content": summary_content, "modelUsed": ai_service.model_name},  
            )  
            logging.info(f"Summary saved for meeting {meeting_id}")  
        else:  
            logging.info(f"No transcript found for meeting {meeting_id}. Skipping summary.")  

        # 3. Mark meeting as inactive and record actual end time  
        await db.meeting.update(  
            where={"id": meeting_id},  
            data={"isActive": False, "actualEnd": datetime.now(timezone.utc)},  
        )  
        logging.info(f"Meeting {meeting_id} closed successfully.")  

        # Optional: trigger Orchestrate tasks (e.g., action items, notifications)  
        # await orchestrate_service.trigger_wrapup_tasks(meeting_id)  

    except Exception as e:  
        logging.error(f"Failed to wrap up meeting {meeting_id}: {e}", exc_info=True)  
        # Could add retry logic or alerting here  
    finally:  
        await lock.release()  
        logging.info(f"Released lock for meeting {meeting_id}")  