from django.apps import AppConfig
from ECHOME.BLOCK_CHAIN import ChainContract
from ECHOME.IPFS import FilebaseIPFS
from .utility_functions import utility_functions

contract = ChainContract()  # contract object
utility_client = utility_functions()
ipfsClient = FilebaseIPFS()  # filebase object



class WorkerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'WORKER'

    def ready(self):
        # Import inside this function — after Django is ready
        try:
            from django_celery_beat.models import PeriodicTask, IntervalSchedule

            # Example: ensure periodic task exists
            schedule, _ = IntervalSchedule.objects.get_or_create(
                every=1,
                period=IntervalSchedule.MINUTES,
            )
            PeriodicTask.objects.get_or_create(
                interval=schedule,
                name='Send Notification Task',
                task='WORKER.tasks.send_notification',
            )
            print("✅ Celery Beat periodic task registered successfully.")
        except Exception as e:
            print(f"[WORKER] Skipping beat schedule setup: {e}")
