from celery import shared_task
import logging
from django.utils import timezone
from ECHOME.SMTP import send_email_with_attachment
from ECHOME.models import TimeCapsule
from datetime import timedelta
from django.utils.timezone import now
from .app import contract, ipfsClient, utility_client
from .models import ScheduledTaskLog

logger = logging.getLogger(__name__)

@shared_task
def send_notification():
    log_entry = ScheduledTaskLog.objects.create(
        task_name="send_notification",
        status="running"
    )
    try:
        logger.info("Executing Celery notification task")

        list_cid = contract.get_expired_data()["cids"]
        print("list of cid", list_cid)

        if not list_cid:
            log_entry.status = "completed"
            log_entry.details = "No expired CIDs found"
            log_entry.save()
            return

        for cid in list_cid:
            try:
                cid = cid.decode('utf-8').strip('\x00').strip() if isinstance(cid, bytes) else cid.strip()
                capsules = TimeCapsule.objects.filter(cid=cid[-12:])
                if capsules.count() == 1:
                    capsule = capsules[0]
                else:
                    current_time = now()
                    capsule = min(
                        capsules,
                        key=lambda record: abs(((record.storage_time + timedelta(seconds=record.unlock_time)) - current_time).total_seconds())
                    )

                data = {
                    'cid': cid,
                    'email': capsule.email,
                    'decryption_pass': capsule.decryption_pass,
                    'storage_time': capsule.storage_time,
                    'file_ext': capsule.file_ext,
                    'file_mime': capsule.file_mime,
                }
                capsule.delete()

                file_dict = ipfsClient.get_file_by_cid(cid)
                if not file_dict:
                    capsule.status = "failed"
                    capsule.save()
                    continue

                decrypted_file = utility_client.decrypt_aes256_cbc(file_dict["bytes"], data['decryption_pass'])
                file_dict['bytes'] = decrypted_file
                if not decrypted_file:
                    capsule.status = "failed"
                    capsule.save()
                    continue

                file_dict['mime_type'] = data['file_mime']
                file_dict['ext'] = data['file_ext']

                diffrance = utility_client.detailed_time_difference(data['storage_time'])
                email_sent = send_email_with_attachment(
                    to_email=data['email'],
                    file_info=file_dict,
                    time=data['storage_time'],
                    time_difference=diffrance,
                )

                if not email_sent:
                    capsule.status = "failed"
                    capsule.save()
                    continue
                else:
                    capsule.status = "sent"
                    capsule.save()

            except TimeCapsule.DoesNotExist:
                ipfsClient.delete_file_by_cid(cid)
                continue

        log_entry.status = "completed"
        log_entry.details = "Task completed successfully"

    except Exception as e:
        logger.error(f"Task failed: {str(e)}")
        log_entry.status = "failed"
        log_entry.details = str(e)
    finally:
        log_entry.completed_at = timezone.now()
        log_entry.save()
