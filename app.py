# app.py (CampaignLauncher v1.1 - Correção de Secrets)

import streamlit as st
import os  # <--- GARANTA QUE ESTA LINHA ESTEJA AQUI
from sqlalchemy import create_engine, text
import pandas as pd

# --- Configuração da Página ---
st.set_page_config(page_title="Campaign Launcher", layout="centered")
st.title("🚀 Campaign Launcher - Lançador de Campanhas")
st.markdown("---")

# --- Conexão com o Banco de Dados (Método Padrão) ---
db_url = os.environ.get("DATABASE_URL")

if not db_url:
    st.error("ERRO CRÍTICO: A variável de ambiente 'DATABASE_URL' não foi encontrada.")
    st.info("Por favor, adicione a Internal Database URL do seu banco 'agency-os-db' nas Environment Variables deste app no Render.")
    st.stop()

# Ajusta a URL para o dialeto do SQLAlchemy
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)

try:
    engine = create_engine(db_url)
except Exception as e:
    st.error(f"Erro ao criar a conexão com o banco de dados: {e}")
    st.stop()

# --- Função para Carregar Clientes do Banco de Dados ---
def carregar_clientes():
    """Busca todos os clientes do banco de dados do AgencyOS."""
    try:
        with engine.connect() as connection:
            query = "SELECT id, nome_empresa, adscode FROM clientes ORDER BY nome_empresa ASC"
            df_clientes = pd.read_sql(query, connection)
            df_clientes['display_name'] = df_clientes['nome_empresa'] + " (" + df_clientes['adscode'] + ")"
            return df_clientes
    except Exception as e:
        if "relation \"clientes\" does not exist" in str(e):
             st.error("A tabela 'clientes' não foi encontrada no banco de dados. Verifique se o AgencyOS já foi executado e criou as tabelas.")
        else:
            st.error(f"Erro ao carregar clientes: {e}")
        return pd.DataFrame(columns=['id', 'display_name'])

# --- Interface Principal ---
st.header("1. Seleção de Cliente")

df_clientes = carregar_clientes()

if not df_clientes.empty:
    cliente_selecionado = st.selectbox(
        "Selecione o cliente para o qual deseja criar a campanha:",
        options=df_clientes['display_name'],
        index=None,
        placeholder="Escolha um cliente..."
    )

    if cliente_selecionado:
        st.success(f"Cliente selecionado: **{cliente_selecionado}**")
        st.info("Próximo passo: Adicionar os campos de configuração da campanha e a lógica da API do Google Ads.")
else:
    st.warning("Nenhum cliente encontrado no banco de dados. Por favor, cadastre clientes no AgencyOS primeiro.")
