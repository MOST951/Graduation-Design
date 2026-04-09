package com.weibo.collector.scheduler;

import lombok.extern.slf4j.Slf4j;
import org.quartz.*;
import org.quartz.impl.StdSchedulerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Component;

import javax.annotation.PostConstruct;

import static org.quartz.JobBuilder.newJob;
import static org.quartz.SimpleScheduleBuilder.simpleSchedule;
import static org.quartz.TriggerBuilder.newTrigger;

/**
 * Schedules recurring data collection tasks.
 * <p>
 * This class uses Quartz to periodically trigger data collection jobs.
 * </p>
 */
@Slf4j
@Component
public class TaskScheduler {

    @Autowired
    private JobManager jobManager;

    private Scheduler scheduler;

    @PostConstruct
    public void init() throws SchedulerException {
        this.scheduler = StdSchedulerFactory.getDefaultScheduler();
        this.scheduler.start();
    }

    public void scheduleTask(String jobName, String groupName, Class<? extends Job> jobClass, int intervalInSeconds) throws SchedulerException {
        JobDetail job = newJob(jobClass)
            .withIdentity(jobName, groupName)
            .build();

        Trigger trigger = newTrigger()
            .withIdentity(jobName + "-trigger", groupName)
            .startNow()
            .withSchedule(simpleSchedule()
                .withIntervalInSeconds(intervalInSeconds)
                .repeatForever())
            .build();

        scheduler.scheduleJob(job, trigger);
    }

    public void pauseTask(String jobName, String groupName) throws SchedulerException {
        scheduler.pauseJob(JobKey.jobKey(jobName, groupName));
    }

    public void resumeTask(String jobName, String groupName) throws SchedulerException {
        scheduler.resumeJob(JobKey.jobKey(jobName, groupName));
    }

    public void cancelTask(String jobName, String groupName) throws SchedulerException {
        scheduler.deleteJob(JobKey.jobKey(jobName, groupName));
    }
    
    // Example usage method
    public void scheduleDefaultTask() {
        log.info("Executing scheduled hourly data collection task.");
        // Example job: crawl the public timeline or a specific user's page
        jobManager.startJob("https://weibo.com/some_topic");
    }
}
