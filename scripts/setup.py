#!/usr/bin/env python3
"""Script de setup para preparar o ambiente de teste."""

import os
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str]) -> bool:
    """Execute command and return success status."""
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✅ {' '.join(cmd)}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {' '.join(cmd)}")
        print(f"   Error: {e.stderr.strip()}")
        return False


def main():
    """Setup the test environment."""
    print("🚀 CONFIGURAÇÃO DO AMBIENTE DE TESTE")
    print("=" * 50)

    success_count = 0
    total_steps = 4

    # Step 1: Install main dependencies
    print("\n1️⃣ Instalando dependências principais...")
    if run_command([sys.executable, "-m", "pip", "install", "-e", "."]):
        success_count += 1

    # Step 2: Install optional dependencies
    print("\n2️⃣ Instalando dependências opcionais...")
    if run_command([sys.executable, "-m", "pip", "install", "python-dotenv"]):
        success_count += 1

    # Step 3: Create directories
    print("\n3️⃣ Criando diretórios necessários...")
    try:
        Path("data").mkdir(exist_ok=True)
        Path("reports").mkdir(exist_ok=True)
        print("✅ Diretórios criados: data/, reports/")
        success_count += 1
    except Exception as e:
        print(f"❌ Erro criando diretórios: {e}")

    # Step 4: Setup .env if not exists
    print("\n4️⃣ Configurando arquivo .env...")
    env_file = Path(".env")
    env_example = Path(".env.example")

    if not env_file.exists() and env_example.exists():
        try:
            env_file.write_text(env_example.read_text())
            print("✅ Arquivo .env criado a partir do .env.example")
            print("⚠️  EDITE o .env com suas credenciais SMTP!")
            success_count += 1
        except Exception as e:
            print(f"❌ Erro criando .env: {e}")
    elif env_file.exists():
        print("✅ Arquivo .env já existe")
        success_count += 1
    else:
        print("❌ .env.example não encontrado")

    # Summary
    print(f"\n📊 Setup concluído: {success_count}/{total_steps} etapas")

    if success_count == total_steps:
        print("\n🎉 SETUP COMPLETO!")
        print("\n📝 PRÓXIMOS PASSOS:")
        print("1. Edite o arquivo .env com suas credenciais SMTP")
        print("2. Execute: python validate_system.py")
        print("3. Execute: python test_end_to_end.py --email seu@email.com")
    else:
        print("\n⚠️  Setup parcialmente concluído. Verifique os erros acima.")

    return 0 if success_count == total_steps else 1


if __name__ == "__main__":
    sys.exit(main())