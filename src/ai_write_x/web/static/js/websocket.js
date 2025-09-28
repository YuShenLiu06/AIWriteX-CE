// WebSocket连接管理  
class WebSocketManager {  
    constructor() {  
        this.ws = null;  
        this.reconnectAttempts = 0;  
        this.maxReconnectAttempts = 5;  
        this.reconnectInterval = 3000;  
        this.callbacks = {  
            onMessage: [],  
            onOpen: [],  
            onClose: [],  
            onError: []  
        };  
    }  
      
    connect() {  
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';  
        const wsUrl = `${protocol}//${window.location.host}/ws/logs`;  
          
        try {  
            this.ws = new WebSocket(wsUrl);  
            this.setupEventListeners();  
        } catch (error) {  
            console.error('WebSocket连接失败:', error);  
            this.handleReconnect();  
        }  
    }  
      
    setupEventListeners() {  
        this.ws.onopen = (event) => {  
            console.log('WebSocket连接已建立');  
            this.reconnectAttempts = 0;  
            this.callbacks.onOpen.forEach(callback => callback(event));  
        };  
          
        this.ws.onmessage = (event) => {  
            try {  
                const data = JSON.parse(event.data);  
                this.callbacks.onMessage.forEach(callback => callback(data));  
            } catch (error) {  
                console.error('解析WebSocket消息失败:', error);  
            }  
        };  
          
        this.ws.onclose = (event) => {  
            console.log('WebSocket连接已断开');  
            this.callbacks.onClose.forEach(callback => callback(event));  
            this.handleReconnect();  
        };  
          
        this.ws.onerror = (error) => {  
            console.error('WebSocket错误:', error);  
            this.callbacks.onError.forEach(callback => callback(error));  
        };  
    }  
      
    handleReconnect() {  
        if (this.reconnectAttempts < this.maxReconnectAttempts) {  
            this.reconnectAttempts++;  
            console.log(`尝试重连 (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);  
              
            setTimeout(() => {  
                this.connect();  
            }, this.reconnectInterval);  
        } else {  
            console.error('WebSocket重连失败，已达到最大重试次数');  
        }  
    }  
      
    send(message) {  
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {  
            this.ws.send(message);  
        } else {  
            console.warn('WebSocket未连接，无法发送消息');  
        }  
    }  
      
    on(event, callback) {  
        if (this.callbacks[event]) {  
            this.callbacks[event].push(callback);  
        }  
    }  
      
    off(event, callback) {  
        if (this.callbacks[event]) {  
            const index = this.callbacks[event].indexOf(callback);  
            if (index > -1) {  
                this.callbacks[event].splice(index, 1);  
            }  
        }  
    }  
      
    close() {  
        if (this.ws) {  
            this.ws.close();  
        }  
    }  
}