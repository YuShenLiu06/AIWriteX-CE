// 通用对话框管理器  
class DialogManager {  
    constructor() {  
        this.activeDialog = null;  
    }  
      
    // 显示确认对话框  
    showConfirm(message, onConfirm, onCancel) {  
        // 移除已存在的对话框  
        const existingDialog = document.querySelector('.custom-confirm-dialog');  
        if (existingDialog) {  
            existingDialog.remove();  
        }  
          
        // 创建遮罩层  
        const overlay = document.createElement('div');  
        overlay.className = 'dialog-overlay';  
          
        // 创建对话框  
        const dialog = document.createElement('div');  
        dialog.className = 'custom-confirm-dialog';  
          
        // 对话框头部  
        const header = document.createElement('div');  
        header.className = 'dialog-header';  
        header.innerHTML = '<h3>系统提示</h3>';  
          
        // 对话框内容  
        const body = document.createElement('div');  
        body.className = 'dialog-body';  
        body.innerHTML = `<p>${message}</p>`;  
          
        // 对话框底部  
        const footer = document.createElement('div');  
        footer.className = 'dialog-footer';  
          
        const cancelBtn = document.createElement('button');  
        cancelBtn.className = 'btn btn-secondary';  
        cancelBtn.textContent = '取消';  
        cancelBtn.addEventListener('click', () => {  
            this.closeDialog();  
            if (onCancel) onCancel();  
        });  
          
        const confirmBtn = document.createElement('button');  
        confirmBtn.className = 'btn btn-primary';  
        confirmBtn.textContent = '确定';  
        confirmBtn.addEventListener('click', () => {  
            this.closeDialog();  
            if (onConfirm) onConfirm();  
        });  
          
        footer.appendChild(cancelBtn);  
        footer.appendChild(confirmBtn);  
          
        // 组装对话框  
        dialog.appendChild(header);  
        dialog.appendChild(body);  
        dialog.appendChild(footer);  
        overlay.appendChild(dialog);  
        document.body.appendChild(overlay);  
          
        this.activeDialog = overlay;  
          
        // ESC键关闭  
        const handleEsc = (e) => {  
            if (e.key === 'Escape') {  
                this.closeDialog();  
                if (onCancel) onCancel();  
                document.removeEventListener('keydown', handleEsc);  
            }  
        };  
        document.addEventListener('keydown', handleEsc);  
          
        // 点击遮罩层关闭  
        overlay.addEventListener('click', (e) => {  
            if (e.target === overlay) {  
                this.closeDialog();  
                if (onCancel) onCancel();  
            }  
        });  
    }  
      
    // 显示提示对话框  
    showAlert(message, type = 'info') {  
        const existingDialog = document.querySelector('.custom-alert-dialog');  
        if (existingDialog) {  
            existingDialog.remove();  
        }  
          
        const overlay = document.createElement('div');  
        overlay.className = 'dialog-overlay';  
          
        const dialog = document.createElement('div');  
        dialog.className = `custom-alert-dialog alert-${type}`;  
          
        const header = document.createElement('div');  
        header.className = 'dialog-header';  
        const icon = type === 'error' ? '❌' : type === 'success' ? '✅' : 'ℹ️';  
        header.innerHTML = `<h3>${icon} 提示</h3>`;  
          
        const body = document.createElement('div');  
        body.className = 'dialog-body';  
        body.innerHTML = `<p>${message}</p>`;  
          
        const footer = document.createElement('div');  
        footer.className = 'dialog-footer';  
          
        const okBtn = document.createElement('button');  
        okBtn.className = 'btn btn-primary';  
        okBtn.textContent = '确定';  
        okBtn.addEventListener('click', () => this.closeDialog());  
          
        footer.appendChild(okBtn);  
          
        dialog.appendChild(header);  
        dialog.appendChild(body);  
        dialog.appendChild(footer);  
        overlay.appendChild(dialog);  
        document.body.appendChild(overlay);  
          
        this.activeDialog = overlay;  
          
        // ESC键关闭  
        const handleEsc = (e) => {  
            if (e.key === 'Escape') {  
                this.closeDialog();  
                document.removeEventListener('keydown', handleEsc);  
            }  
        };  
        document.addEventListener('keydown', handleEsc);  
          
        overlay.addEventListener('click', (e) => {  
            if (e.target === overlay) {  
                this.closeDialog();  
            }  
        });  
    }  
      
    // 关闭对话框  
    closeDialog() {  
        if (this.activeDialog) {  
            this.activeDialog.remove();  
            this.activeDialog = null;  
        }  
    }  
}  
  
// 创建全局实例  
window.dialogManager = new DialogManager();