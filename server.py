# ============================================================
# SERVIDOR DE UPDATES - Exemplo para Railway
# ============================================================
# Este é um exemplo completo de servidor que você pode usar no Railway
# Inclui os endpoints necessários para o sistema de auto-update

from flask import Flask, request, jsonify, send_file
import os
import json
from pathlib import Path
from packaging import version as pkg_version

app = Flask(__name__)

# Configurações
UPLOAD_KEY = "moneybot-secret-2024"  # Mesma chave do publish_update.py
UPDATES_DIR = Path("updates")  # Pasta onde ficam os executáveis
VERSIONS_FILE = Path("versions.json")  # Arquivo com informações das versões

# Cria pasta de updates se não existir
UPDATES_DIR.mkdir(exist_ok=True)

# Carrega versões salvas
def load_versions():
    """Carrega informações das versões"""
    if VERSIONS_FILE.exists():
        with open(VERSIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_versions(versions_data):
    """Salva informações das versões"""
    with open(VERSIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(versions_data, f, indent=2, ensure_ascii=False)

def get_latest_version():
    """Retorna a versão mais recente"""
    versions = load_versions()
    if not versions:
        return None
    
    # Encontra a versão mais recente
    latest = None
    latest_version = None
    
    for ver, info in versions.items():
        if latest_version is None or pkg_version.parse(ver) > pkg_version.parse(latest_version):
            latest_version = ver
            latest = info
    
    return latest

@app.route('/update/check', methods=['GET'])
def check_update():
    """
    Endpoint para verificar se há atualização disponível
    
    Parâmetros:
        current_version: Versão atual do cliente (ex: 1.0.0)
    
    Retorna JSON:
        {
            "version": "1.0.1",
            "changelog": "Descrição",
            "download_url": "https://...",
            "file_size": 12345678
        }
    """
    current_version = request.args.get('current_version', '0.0.0')
    
    try:
        latest = get_latest_version()
        
        if not latest:
            # Não há versões publicadas
            return jsonify({
                "version": current_version,
                "changelog": "",
                "download_url": "",
                "file_size": 0
            }), 200
        
        latest_version = latest.get('version', '0.0.0')
        
        # Compara versões
        if pkg_version.parse(latest_version) > pkg_version.parse(current_version):
            # Há atualização disponível
            download_url = f"{request.scheme}://{request.host}/update/download/{latest_version}"
            
            return jsonify({
                "version": latest_version,
                "changelog": latest.get('changelog', 'Nova atualização disponível'),
                "download_url": download_url,
                "file_size": latest.get('file_size', 0)
            }), 200
        else:
            # Não há atualização (já está na versão mais recente)
            return jsonify({
                "version": current_version,
                "changelog": "",
                "download_url": "",
                "file_size": 0
            }), 200
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update/download/<version>', methods=['GET'])
def download_update(version):
    """
    Endpoint para baixar o executável de uma versão específica
    
    Parâmetros:
        version: Versão a ser baixada (ex: 1.0.1)
    """
    try:
        versions = load_versions()
        
        if version not in versions:
            return jsonify({"error": "Versão não encontrada"}), 404
        
        file_path = versions[version].get('file_path')
        
        if not file_path or not os.path.exists(file_path):
            return jsonify({"error": "Arquivo não encontrado"}), 404
        
        return send_file(
            file_path,
            as_attachment=True,
            download_name='MoneyBot.exe',
            mimetype='application/octet-stream'
        )
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update/upload', methods=['POST'])
def upload_update():
    """
    Endpoint para fazer upload de uma nova versão
    
    Parâmetros (form-data):
        key: Chave de autenticação
        version: Versão (ex: 1.0.1)
        changelog: Descrição das mudanças
        file: Arquivo executável
    
    Retorna JSON com informações da versão publicada
    """
    try:
        # Verifica chave
        upload_key = request.form.get('key')
        if upload_key != UPLOAD_KEY:
            return jsonify({"error": "Chave inválida"}), 401
        
        # Obtém dados
        version = request.form.get('version')
        changelog = request.form.get('changelog', 'Nova atualização')
        
        if not version:
            return jsonify({"error": "Versão não fornecida"}), 400
        
        # Verifica se arquivo foi enviado
        if 'file' not in request.files:
            return jsonify({"error": "Arquivo não fornecido"}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({"error": "Arquivo vazio"}), 400
        
        # Salva arquivo
        file_path = UPDATES_DIR / f"MoneyBot_{version}.exe"
        file.save(file_path)
        
        file_size = os.path.getsize(file_path)
        
        # Salva informações da versão
        versions = load_versions()
        versions[version] = {
            "version": version,
            "changelog": changelog,
            "file_path": str(file_path),
            "file_size": file_size,
            "uploaded_at": str(Path(file_path).stat().st_mtime)
        }
        save_versions(versions)
        
        # Retorna informações
        return jsonify({
            "success": True,
            "version_info": {
                "version": version,
                "changelog": changelog,
                "file_size": file_size
            }
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health', methods=['GET'])
def health():
    """Endpoint de health check"""
    return jsonify({"status": "ok"}), 200

@app.route('/', methods=['GET'])
def index():
    """Página inicial"""
    latest = get_latest_version()
    
    if latest:
        return jsonify({
            "service": "MoneyBot Update Server",
            "latest_version": latest.get('version'),
            "endpoints": {
                "check": "/update/check?current_version=X.X.X",
                "download": "/update/download/<version>",
                "upload": "/update/upload (POST)"
            }
        }), 200
    else:
        return jsonify({
            "service": "MoneyBot Update Server",
            "status": "No versions published yet",
            "endpoints": {
                "check": "/update/check?current_version=X.X.X",
                "download": "/update/download/<version>",
                "upload": "/update/upload (POST)"
            }
        }), 200

if __name__ == '__main__':
    # Para desenvolvimento local
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=False)
else:
    # Para produção (Railway)
    # O Railway automaticamente define a variável PORT
    pass

