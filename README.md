# Linux System Health Check

A Bash script to check Linux system resources and network connectivity,
then save the results to a report.

## Features

-   Disk usage --- `df -h`
-   Memory usage --- `free -h`
-   CPU load --- `uptime`
-   Failed systemd services --- `systemctl --failed --no-legend`
-   Top CPU processes ---
    `ps -eo user,pid,%cpu,%mem,command --sort=-%cpu | head -6`
-   Top memory processes ---
    `ps -eo user,pid,%cpu,%mem,command --sort=-%mem | head -6`
-   System uptime --- `uptime -p`
-   Recent error logs --- `journalctl -b -p 3 --no-pager`
-   Network interfaces and IP addresses --- `ip a`
-   Routing table --- `ip route`
-   Listening ports --- `ss -tulnp`
-   Internet connectivity --- `ping -c 3 8.8.8.8`
-   DNS/connectivity test --- `ping -c 3 google.com`
-   Save the report --- `tee "$LOGFILE"`

## Screenshots

Add your project screenshots here.

```{=html}
<!-- Replace the placeholders below with your image filenames or GitHub image URLs. -->
```
### 1. Running the script

```{=html}
<!-- Add screenshot here -->
```
![Running the health check](screenshots/health-check-run.png)

### 2. Health report output

```{=html}
<!-- Add screenshot here -->
```
![Health report output](screenshots/health-report.png)

### 3. Network diagnostics

```{=html}
<!-- Add screenshot here -->
```
![Network diagnostics](screenshots/network-diagnostics.png)

### 4. Cron schedule

```{=html}
<!-- Add screenshot here -->
```
![Cron schedule](screenshots/cron-schedule.png)

## Run the script

``` bash
chmod +x ~/health-check.sh
~/health-check.sh
```

The report is saved to `~/health-report.txt`.

## Schedule it every day at 07:00

Start cron on Ubuntu/WSL:

``` bash
sudo service cron start
```

Edit the user crontab:

``` bash
crontab -e
```

Add the following line, replacing the path with your actual home
directory:

``` cron
0 7 * * * /home/YOUR_USERNAME/health-check.sh
```

Verify the scheduled job:

``` bash
crontab -l
```

## Notes

-   `df -h` reports disk usage; `free -h` reports memory usage.
-   `systemctl` and `journalctl` may be limited or unavailable in some
    WSL configurations.
-   `ping` can fail when ICMP is blocked, even if internet access works.
-   `ss -tulnp` lists listening sockets; process details may require
    elevated privileges.
