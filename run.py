from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # 从环境变量读取配置，便于生产环境部署
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('DEBUG', 'False').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)