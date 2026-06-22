# AIWriteX CLI

Lightweight CLI client for AIWriteX server.

## Installation

```bash
pip install -e ./client
```

## Usage

```bash
# Configure connection
aiwritex config set base_url http://127.0.0.1:8888
aiwritex config set api_key your_api_key

# Generate content
aiwritex generate run --topic "AI技术趋势"

# Manage articles
aiwritex articles list
aiwritex articles publish --article-paths path1,path2 --account-indices 0

# Manage templates
aiwritex templates list
aiwritex templates create --name my-template --category tech --content "<html>...</html>"

# Knowledge base
aiwritex knowledge text-list
aiwritex knowledge image-upload --file image.jpg --description "AI technology"

# Tasks
aiwritex tasks list
aiwritex tasks create --name daily-news --topic "每日科技新闻" --schedule-type fixed_time --time-of-day 09:00

# Convert
aiwritex convert wechat --url https://mp.weixin.qq.com/s/xxx --output-type template

# System
aiwritex system health
```

## Configuration

Configuration is stored in `~/.aiwritex/config.yaml`:

```yaml
base_url: http://127.0.0.1:8888
api_key: null
username: null
password: null
timeout: 30
```

## Commands

- `config` - Manage CLI configuration
- `articles` - Manage articles
- `generate` - Generate content
- `templates` - Manage templates
- `knowledge` - Manage knowledge base
- `tasks` - Manage scheduled tasks
- `convert` - Convert WeChat articles
- `system` - System health check
