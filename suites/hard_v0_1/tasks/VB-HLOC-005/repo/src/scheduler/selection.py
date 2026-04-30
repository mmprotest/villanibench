def runnable_jobs(jobs):
    # BUG: source-of-truth implementation is stale.
    return [j for j in jobs if j.get("cron")]
