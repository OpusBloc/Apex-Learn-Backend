# backend/app/fixes/critical_fixes.py
"""
Critical bug fixes and integration improvements for ApexLearn platform
"""

import os
import logging
from datetime import datetime, timedelta
from functools import wraps
import asyncio
from typing import Dict, List, Optional, Any
import redis
from flask import Flask, request, g
from flask_limiter import Limiter
from flask_caching import Cache
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============ CRITICAL FIX 1: Database Connection Pool Management ============
class DatabaseConnectionManager:
    """Properly manage database connections to prevent connection leaks"""
    
    def __init__(self, app: Flask):
        self.app = app
        self.setup_connection_pool()
    
    def setup_connection_pool(self):
        """Configure SQLAlchemy connection pool"""
        self.app.config.update({
            'SQLALCHEMY_ENGINE_OPTIONS': {
                'pool_size': 20,
                'pool_recycle': 3600,
                'pool_pre_ping': True,
                'max_overflow': 40,
                'connect_args': {
                    'connect_timeout': 10,
                    'application_name': 'apexlearn'
                }
            }
        })
    
    @staticmethod
    def close_db_session(exception=None):
        """Ensure database sessions are properly closed"""
        from ..models import db
        if exception:
            db.session.rollback()
        db.session.remove()


# ============ CRITICAL FIX 2: Async Task Queue Management ============
class AsyncTaskManager:
    """Properly handle async tasks without blocking main thread"""
    
    def __init__(self):
        self.loop = None
        self.executor = None
    
    def setup(self):
        """Setup async event loop for Flask"""
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
    
    def run_async(self, coro):
        """Run async function in Flask context"""
        if not asyncio.iscoroutine(coro):
            raise TypeError("Expected coroutine")
        
        # Create new event loop for thread safety
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


# ============ CRITICAL FIX 3: Redis Connection Pool ============
class RedisConnectionPool:
    """Manage Redis connections efficiently"""
    
    def __init__(self, app: Flask):
        self.pool = redis.ConnectionPool(
            host=app.config.get('REDIS_HOST', 'localhost'),
            port=app.config.get('REDIS_PORT', 6379),
            db=0,
            max_connections=50,
            socket_connect_timeout=5,
            socket_timeout=5,
            retry_on_timeout=True,
            health_check_interval=30
        )
        self.redis_client = redis.Redis(connection_pool=self.pool)
    
    def get_client(self) -> redis.Redis:
        """Get Redis client from pool"""
        return self.redis_client
    
    def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            self.redis_client.ping()
            return True
        except redis.ConnectionError:
            logger.error("Redis connection failed")
            return False


# ============ CRITICAL FIX 4: Rate Limiting with User Context ============
def setup_rate_limiting(app: Flask):
    """Setup proper rate limiting with user-specific limits"""
    
    def get_remote_address():
        """Get real IP address behind proxy"""
        return request.headers.get('X-Real-IP', request.remote_addr)
    
    def get_user_id():
        """Get user ID for authenticated requests"""
        from flask_jwt_extended import get_jwt_identity
        try:
            return str(get_jwt_identity())
        except:
            return get_remote_address()
    
    limiter = Limiter(
        app=app,
        key_func=get_user_id,
        default_limits=["1000 per hour", "100 per minute"],
        storage_uri=f"redis://{app.config['REDIS_HOST']}:{app.config['REDIS_PORT']}",
        strategy="fixed-window-elastic-expiry"
    )
    
    # Specific endpoint limits
    limiter.limit("5 per minute")(app.view_functions.get('auth.login'))
    limiter.limit("3 per minute")(app.view_functions.get('auth.register'))
    limiter.limit("10 per minute")(app.view_functions.get('chat.chat_with_tutor'))
    
    return limiter


# ============ CRITICAL FIX 5: Caching Strategy ============
class CacheManager:
    """Implement proper caching strategy"""
    
    def __init__(self, app: Flask):
        self.cache = Cache(app, config={
            'CACHE_TYPE': 'redis',
            'CACHE_REDIS_HOST': app.config['REDIS_HOST'],
            'CACHE_REDIS_PORT': app.config['REDIS_PORT'],
            'CACHE_DEFAULT_TIMEOUT': 300,
            'CACHE_KEY_PREFIX': 'apexlearn_'
        })
    
    def cache_user_data(self, timeout=300):
        """Cache user-specific data"""
        def decorator(f):
            @wraps(f)
            def wrapped(*args, **kwargs):
                from flask_jwt_extended import get_jwt_identity
                user_id = get_jwt_identity()
                cache_key = f"user_{user_id}_{f.__name__}_{str(args)}_{str(kwargs)}"
                
                cached = self.cache.get(cache_key)
                if cached is not None:
                    return cached
                
                result = f(*args, **kwargs)
                self.cache.set(cache_key, result, timeout=timeout)
                return result
            
            return wrapped
        return decorator
    
    def invalidate_user_cache(self, user_id: int):
        """Invalidate all cache for a user"""
        pattern = f"apexlearn_user_{user_id}_*"
        redis_client = redis.from_url(
            f"redis://{current_app.config['REDIS_HOST']}:{current_app.config['REDIS_PORT']}"
        )
        for key in redis_client.scan_iter(match=pattern):
            redis_client.delete(key)


# ============ CRITICAL FIX 6: Error Handling and Monitoring ============
def setup_error_handling(app: Flask):
    """Setup comprehensive error handling and monitoring"""
    
    # Initialize Sentry for production
    if app.config.get('FLASK_ENV') == 'production':
        sentry_sdk.init(
            dsn=app.config.get('SENTRY_DSN'),
            integrations=[FlaskIntegration()],
            traces_sample_rate=0.1,
            profiles_sample_rate=0.1,
            environment=app.config.get('FLASK_ENV')
        )
    
    @app.errorhandler(Exception)
    def handle_exception(error):
        """Global exception handler"""
        logger.error(f"Unhandled exception: {str(error)}", exc_info=True)
        
        if app.config.get('FLASK_ENV') == 'production':
            # Don't expose internal errors in production
            return {'error': 'An internal error occurred'}, 500
        else:
            return {'error': str(error)}, 500
    
    @app.errorhandler(404)
    def handle_404(error):
        return {'error': 'Resource not found'}, 404
    
    @app.errorhandler(429)
    def handle_rate_limit(error):
        return {'error': 'Too many requests. Please try again later.'}, 429


# ============ CRITICAL FIX 7: WebSocket Connection Management ============
class WebSocketManager:
    """Properly manage WebSocket connections"""
    
    def __init__(self, socketio):
        self.socketio = socketio
        self.connections = {}
        self.setup_handlers()
    
    def setup_handlers(self):
        """Setup WebSocket event handlers"""
        
        @self.socketio.on('connect')
        def handle_connect():
            from flask_jwt_extended import decode_token
            try:
                token = request.args.get('token')
                if not token:
                    return False
                
                decoded = decode_token(token)
                user_id = decoded['sub']
                
                # Store connection
                self.connections[request.sid] = {
                    'user_id': user_id,
                    'connected_at': datetime.utcnow()
                }
                
                # Join user room
                join_room(f"user_{user_id}")
                
                logger.info(f"User {user_id} connected via WebSocket")
                return True
                
            except Exception as e:
                logger.error(f"WebSocket connection failed: {e}")
                return False
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            if request.sid in self.connections:
                user_id = self.connections[request.sid]['user_id']
                leave_room(f"user_{user_id}")
                del self.connections[request.sid]
                logger.info(f"User {user_id} disconnected")
    
    def emit_to_user(self, user_id: int, event: str, data: Any):
        """Emit event to specific user"""
        self.socketio.emit(event, data, room=f"user_{user_id}")


# ============ CRITICAL FIX 8: AI Service Integration Fixes ============
class AIServiceFixes:
    """Fix AI service integration issues"""
    
    @staticmethod
    def fix_openai_timeout():
        """Handle OpenAI API timeouts properly"""
        import openai
        from tenacity import retry, wait_exponential, stop_after_attempt
        
        @retry(
            wait=wait_exponential(multiplier=1, min=4, max=10),
            stop=stop_after_attempt(3)
        )
        def call_openai_with_retry(messages, model="gpt-4", **kwargs):
            try:
                response = openai.ChatCompletion.create(
                    model=model,
                    messages=messages,
                    timeout=30,
                    **kwargs
                )
                return response
            except openai.error.Timeout:
                logger.error("OpenAI API timeout")
                raise
            except openai.error.APIError as e:
                logger.error(f"OpenAI API error: {e}")
                raise
        
        return call_openai_with_retry
    
    @staticmethod
    def fix_rag_retrieval():
        """Fix RAG retrieval issues"""
        def improved_retrieval(query: str, k: int = 5) -> List[Dict]:
            """Improved retrieval with fallback"""
            try:
                # Primary retrieval using embeddings
                results = retrieve_with_embeddings(query, k)
                
                if len(results) < k:
                    # Fallback to keyword search
                    keyword_results = retrieve_with_keywords(query, k - len(results))
                    results.extend(keyword_results)
                
                # Deduplicate and rerank
                results = deduplicate_results(results)
                results = rerank_results(results, query)
                
                return results[:k]
                
            except Exception as e:
                logger.error(f"Retrieval error: {e}")
                return []
        
        return improved_retrieval


# ============ CRITICAL FIX 9: Payment Integration Fixes ============
class PaymentIntegrationFixes:
    """Fix payment gateway integration issues"""
    
    @staticmethod
    def verify_payment_webhook(provider: str, payload: Dict, signature: str) -> bool:
        """Properly verify payment webhooks"""
        import hmac
        import hashlib
        
        if provider == 'razorpay':
            secret = current_app.config['RAZORPAY_WEBHOOK_SECRET']
            expected = hmac.new(
                secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected, signature)
        
        elif provider == 'stripe':
            import stripe
            stripe.api_key = current_app.config['STRIPE_SECRET_KEY']
            
            try:
                stripe.Webhook.construct_event(
                    payload, 
                    signature, 
                    current_app.config['STRIPE_WEBHOOK_SECRET']
                )
                return True
            except:
                return False
        
        return False
    
    @staticmethod
    def handle_payment_failure(transaction_id: str, reason: str):
        """Properly handle payment failures"""
        from ..models import Transaction, Subscription
        
        transaction = Transaction.query.filter_by(transaction_id=transaction_id).first()
        if transaction:
            transaction.status = 'failed'
            transaction.gateway_response = {'failure_reason': reason}
            
            # Notify user
            notification_service.send_notification(
                transaction.subscription.user_id,
                'payment_failed',
                f'Payment failed: {reason}'
            )
            
            db.session.commit()


# ============ CRITICAL FIX 10: Performance Optimizations ============
class PerformanceOptimizations:
    """Critical performance optimizations"""
    
    @staticmethod
    def optimize_database_queries():
        """Add query optimization middleware"""
        from flask_sqlalchemy import get_debug_queries
        
        def log_slow_queries():
            for query in get_debug_queries():
                if query.duration >= 0.5:
                    logger.warning(
                        f"Slow query: {query.statement[:100]}... "
                        f"Duration: {query.duration}s"
                    )
        
        return log_slow_queries
    
    @staticmethod
    def batch_database_operations():
        """Batch database operations for efficiency"""
        from sqlalchemy import insert
        
        def batch_insert(model, data: List[Dict], batch_size: int = 1000):
            """Efficiently insert multiple records"""
            for i in range(0, len(data), batch_size):
                batch = data[i:i + batch_size]
                stmt = insert(model).values(batch)
                db.session.execute(stmt)
            
            db.session.commit()
        
        return batch_insert
    
    @staticmethod
    def implement_query_caching():
        """Cache frequently used queries"""
        def cached_query(query, timeout=300):
            cache_key = f"query_{str(query)}"
            
            cached = current_app.cache.get(cache_key)
            if cached is not None:
                return cached
            
            result = query.all()
            current_app.cache.set(cache_key, result, timeout=timeout)
            
            return result
        
        return cached_query


# ============ Application Factory with All Fixes ============
def create_app_with_fixes(config_name='development'):
    """Create Flask app with all critical fixes applied"""
    from flask import Flask
    from flask_migrate import Migrate
    from flask_jwt_extended import JWTManager
    from flask_socketio import SocketIO
    from flask_cors import CORS
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(f'config.{config_name}')
    
    # Initialize database
    from ..models import db
    db.init_app(app)
    
    # Apply critical fixes
    db_manager = DatabaseConnectionManager(app)
    app.teardown_appcontext(db_manager.close_db_session)
    
    # Setup async task manager
    async_manager = AsyncTaskManager()
    async_manager.setup()
    app.async_manager = async_manager
    
    # Setup Redis
    redis_pool = RedisConnectionPool(app)
    app.redis = redis_pool.get_client()
    
    # Setup rate limiting
    limiter = setup_rate_limiting(app)
    
    # Setup caching
    cache_manager = CacheManager(app)
    app.cache_manager = cache_manager
    
    # Setup error handling
    setup_error_handling(app)
    
    # Setup WebSocket
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    ws_manager = WebSocketManager(socketio)
    app.ws_manager = ws_manager
    
    # Setup CORS
    CORS(app, origins=app.config.get('ALLOWED_ORIGINS', ['*']))
    
    # Setup JWT
    jwt = JWTManager(app)
    
    # Setup migrations
    migrate = Migrate(app, db)
    
    # Register blueprints with error handling
    from ..routes import api_routes
    for blueprint in [
        api_routes.auth_bp,
        api_routes.student_bp,
        api_routes.parent_bp,
        api_routes.teacher_bp,
        api_routes.quiz_bp,
        api_routes.study_bp,
        api_routes.chat_bp,
        api_routes.analytics_bp,
        api_routes.payment_bp
    ]:
        app.register_blueprint(blueprint)
    
    # Add performance monitoring
    if app.config.get('FLASK_ENV') == 'development':
        app.after_request(PerformanceOptimizations.optimize_database_queries())
    
    return app, socketio


# ============ Health Check Endpoint ============
def add_health_check(app: Flask):
    """Add comprehensive health check endpoint"""
    
    @app.route('/health', methods=['GET'])
    def health_check():
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'checks': {}
        }
        
        # Check database
        try:
            from ..models import db
            db.session.execute('SELECT 1')
            health_status['checks']['database'] = 'ok'
        except:
            health_status['checks']['database'] = 'failed'
            health_status['status'] = 'unhealthy'
        
        # Check Redis
        try:
            app.redis.ping()
            health_status['checks']['redis'] = 'ok'
        except:
            health_status['checks']['redis'] = 'failed'
            health_status['status'] = 'unhealthy'
        
        # Check external services
        try:
            import openai
            # Don't actually call API, just check if configured
            if app.config.get('OPENAI_API_KEY'):
                health_status['checks']['openai'] = 'configured'
            else:
                health_status['checks']['openai'] = 'not_configured'
        except:
            health_status['checks']['openai'] = 'error'
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code


if __name__ == "__main__":
    # Create app with all fixes
    app, socketio = create_app_with_fixes('development')
    add_health_check(app)
    
    # Run with proper configuration
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=app.config.get('DEBUG', False),
        use_reloader=False
    )