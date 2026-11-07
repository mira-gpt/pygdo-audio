"""Track only GDO-owned audio jobs; never touch unrelated desktop streams."""
import asyncio


class PlaybackTasks:
    tasks = set()

    @classmethod
    def start(cls, coroutine):
        task = asyncio.create_task(coroutine)
        cls.tasks.add(task)
        task.add_done_callback(cls.tasks.discard)
        return task

    @classmethod
    async def stop(cls):
        current = asyncio.current_task()
        active = [task for task in tuple(cls.tasks) if task is not current and not task.done()]
        for task in active:
            task.cancel()
        if active:
            await asyncio.gather(*active, return_exceptions=True)
        return len(active)
