class TemplateEditor {  
    constructor() {  
        this.editor = null;  
        this.currentTemplate = null;  
    }  
      
    async init(containerId) {  
        // 加载Monaco Editor (CDN或本地)  
        require.config({   
            paths: { 'vs': 'https://cdn.jsdelivr.net/npm/monaco-editor@0.45.0/min/vs' }  
        });  
          
        require(['vs/editor/editor.main'], () => {  
            this.editor = monaco.editor.create(document.getElementById(containerId), {  
                language: 'html',  
                theme: 'vs-dark',  
                automaticLayout: true,  
                minimap: { enabled: true },  
                formatOnPaste: true,  
                formatOnType: true,  
                // HTML特定配置  
                suggest: {  
                    snippetsPreventQuickSuggestions: false  
                }  
            });  
              
            // 实时预览  
            this.editor.onDidChangeModelContent(() => {  
                this.updatePreview();  
            });  
        });  
    }  
      
    async loadTemplate(templatePath) {  
        const response = await fetch(`/api/templates/content/${encodeURIComponent(templatePath)}`);  
        const content = await response.text();  
        this.editor.setValue(content);  
        this.currentTemplate = templatePath;  
    }  
      
    async saveTemplate() {  
        const content = this.editor.getValue();  
        const response = await fetch(`/api/templates/content/${encodeURIComponent(this.currentTemplate)}`, {  
            method: 'PUT',  
            headers: { 'Content-Type': 'text/html' },  
            body: content  
        });  
        return response.ok;  
    }  
      
    updatePreview() {  
        const content = this.editor.getValue();  
        const previewFrame = document.getElementById('editor-preview-frame');  
        if (previewFrame) {  
            previewFrame.srcdoc = content;  
        }  
    }  
}