```
Filename: 336-randomize-guard-retries.md
Title: Randomized schedule for guard retries
Author: Nick Mathewson
Created: 2021-10-22
Status: Accepted
```

# Introduction

When we notice that a guard isn't working, we don't mark it as retriable
until a certain interval has passed.  Currently, these intervals are
fixed, as described in the documentation for `GUARDS_RETRY_SCHED` in
`guard-spec` appendix A.1.  Here we propose using a randomized retry
interval instead, based on the same decorrelated-jitter algorithm we use
for directory retries.

The upside of this approach is that it makes our behavior in
the presence of an unreliable network a bit harder for an attacker to
predict. It also means that if a guard goes down for a while, its
clients will notice that it is up at staggered times, rather than
probing it in lock-step.

The downside of this approach is that we can, if we get unlucky
enough, completely fail to notice that a preferred guard is online when
we would otherwise have noticed sooner.

Note that when a guard is marked retriable, it isn't necessarily retried
immediately.  Instead, its status is changed from "Unreachable" to
"Unknown", which will cause it to get retried.

For reference, our previous schedule was:

```
   {param:PRIMARY_GUARDS_RETRY_SCHED}
      -- every 10 minutes for the first six hours,
      -- every 90 minutes for the next 90 hours,
      -- every 4 hours for the next 3 days,
      -- every 9 hours thereafter.

   {param:GUARDS_RETRY_SCHED} --
      -- every hour for the first six hours,
      -- every 4 hours for the next 90 hours,
      -- every 18 hours for the next 3 days,
      -- every 36 hours thereafter.
```

# The new algorithm

We re-use the decorrelated-jitter algorithm from `dir-spec` section 5.5.
The specific formula used to compute the 'i+1'th delay is:

```
Delay_{i+1} = MIN(cap, random_between(lower_bound, upper_bound))
where upper_bound = MAX(lower_bound+1, Delay_i * 3)
      lower_bound = MAX(1, base_delay).
```

For primary guards, we set base_delay to 30 seconds and cap to 6 hours.

For non-primary guards, we set base_delay to 10 minutes and cap to 36
hours.

(These parameters were selected by simulating the results of using them
until they looked "a bit more aggressive" than the current algorithm, but
not too much.)

The average behavior for the new primary schedule is:

```
First 1.0 hours: 10.14283 attempts. (Avg delay 4m 47.41s)
First 6.0 hours: 19.02377 attempts. (Avg delay 15m 36.95s)
First 96.0 hours: 56.11173 attempts. (Avg delay 1h 40m 3.13s)
First 168.0 hours: 83.67091 attempts. (Avg delay 1h 58m 43.16s)
Steady state: 2h 36m 44.63s between attempts.
```

The average behavior for the new non-primary schedule is:

```
First 1.0 hours: 3.08069 attempts. (Avg delay 14m 26.08s)
First 6.0 hours: 8.1473 attempts. (Avg delay 35m 25.27s)
First 96.0 hours: 22.57442 attempts. (Avg delay 3h 49m 32.16s)
First 168.0 hours: 29.02873 attempts. (Avg delay 5h 27m 2.36s)
Steady state: 11h 15m 28.47s between attempts.
```

