# seasonal-foods-scraper
![python](https://img.shields.io/badge/python-3.10-blue)
![docker](https://img.shields.io/badge/docker-2.29.6-blue)
![release](https://img.shields.io/github/v/release/sasakikensuke/scraping)

Alerting program that scrapes [Tokyo Metropolitan Central Wholesale Market](https://www.shijou-nippo.metro.tokyo.lg.jp) for fresh foods and sends them via email using Docker.


# Setup (Command Prompt for Windows / Terminal for Mac)
### Change to your working directory
```
cd path/to/your/directory
```
### Get the source code
```
git clone https://github.com/sasakikensuke/scraping
```
### Update settings
Update `config.yaml`, `secret.yaml`, and `cron.d/daily`.

# Run Script
### Move to the Dockerfile directory
```
cd scraping
```
### Start Docker
Build image.
```
docker build -t foods-scraper -f Dockerfile .
```
Run container.
```
docker run -d --name foods-scraper -v ./record:/app/record -v ./config.yaml:/app/config.yaml -v ./secret.yaml:/app/secret.yaml -v ./cron.d:/app/cron.d foods-scraper 
```
### Start Historical
```
docker exec -d foods-scraper sh -lc "cd /app && python /app/handler_historical.py >>/proc/1/fd/1 2>>/proc/1/fd/2"
```

### Stop Historical
```
docker exec foods-scraper pkill -f "python /app/handler_historical.py"
```

### Start Daily
```
docker exec -d foods-scraper sh -lc "dos2unix /app/cron.d/daily && crontab /app/cron.d/daily && cron"
```
Scraped values are saved to record/results.csv and trend/alert emails are sent accordingly.

### Stop Daily
```
docker exec foods-scraper pkill cron
```

### Stop and remove Docker
```
docker stop foods-scraper && docker rm --volumes foods-scraper && docker rmi foods-scraper
```

