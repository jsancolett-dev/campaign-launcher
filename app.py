# app.py (CampaignLauncher v2.0 - Campos da Campanha)

import streamlit as st
import os
from sqlalchemy import create_engine, text
import pandas as pd

# --- Configuração da Página ---
st.set_page_config(page_title="Campaign Launcher", layout="centered")
st.title("🚀 Campaign Launcher - Lançador de Campanhas")
st.markdown("---")

# --- Conexão com o Banco de Dados ---
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    st.error("ERRO CRÍTICO: A variável de ambiente 'DATABASE_URL' não foi encontrada.")
    st.stop()
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
try:
    engine = create_engine(db_url)
except Exception as e:
    st.error(f"Erro ao criar a conexão com o banco de dados: {e}")
    st.stop()

# --- Função para Carregar Clientes ---
@st.cache_data(ttl=600) # Adiciona cache para não recarregar a cada interação
def carregar_clientes():
    try:
        with engine.connect() as connection:
            query = "SELECT id, nome_empresa, adscode FROM clientes ORDER BY nome_empresa ASC"
            df_clientes = pd.read_sql(query, connection)
            df_clientes['display_name'] = df_clientes['nome_empresa'] + " (" + df_clientes['adscode'] + ")"
            return df_clientes
    except Exception as e:
        st.error(f"Erro ao carregar clientes: {e}")
        return pd.DataFrame(columns=['id', 'display_name'])

# --- Interface Principal ---
st.header("1. Seleção de Cliente")
df_clientes = carregar_clientes()

if df_clientes.empty:
    st.warning("Nenhum cliente encontrado no banco de dados. Cadastre clientes no AgencyOS primeiro.")
    st.stop()

cliente_selecionado = st.selectbox(
    "Selecione o cliente:",
    options=df_clientes['display_name'],
    index=None,
    placeholder="Escolha um cliente..."
)

# O restante do formulário só aparece se um cliente for selecionado
if cliente_selecionado:
    st.success(f"Cliente selecionado: **{cliente_selecionado}**")
    st.markdown("---")
    
    # --- Seção 2: Configurações da Campanha ---
    st.header("2. Configurações da Campanha no Google Ads")

    with st.form("campaign_form"):
        # Removemos a seleção de MCC por enquanto para simplificar.
        # Assumimos que as credenciais já dão acesso.
        customer_id = st.text_input(
            "ID da Conta do Cliente no Google Ads*",
            placeholder="Ex: 123-456-7890 (sem os hífens)"
        )
        landing_page = st.text_input(
            "URL da Landing Page do Cliente*",
            placeholder="https://www.sitedopsicologo.com.br/terapia"
         )
        phone_number = st.text_input(
            "Número de Telefone para o Anúncio (WhatsApp)*",
            placeholder="Ex: 5511999998888 (formato internacional)"
        )
        daily_budget_brl = st.number_input(
            "Orçamento Diário (R$)*",
            min_value=10.0,
            value=50.0,
            step=5.0
        )

        # --- Seção 3: Template do Anúncio ---
        st.markdown("---")
        st.header("3. Seleção do Template de Anúncio")

        # Por enquanto, uma lista simples. No futuro, podemos buscar do banco.
        templates = {
            "Psicologia - Terapia de Ansiedade": "template_ansiedade",
            "Psicologia - Terapia de Casal": "template_casal",
            "Psiquiatria - Consulta Geral": "template_psiquiatria"
        }
        template_selecionado = st.selectbox(
            "Selecione o modelo de campanha:",
            options=templates.keys()
        )

        # Botão de submit do formulário
        submitted = st.form_submit_button("🚀 Lançar Campanha!")

        if submitted:
            # Validação dos campos
            if not all([customer_id, landing_page, phone_number, daily_budget_brl]):
                st.warning("Por favor, preencha todos os campos obrigatórios (*).")
            else:
                st.info("Coletando informações... Próximo passo será chamar a API do Google Ads.")
                
                # Apenas para visualização dos dados coletados
                st.write("Dados que serão enviados para a API:")
                st.json({
                    "cliente_agencyos": cliente_selecionado,
                    "google_customer_id": customer_id,
                    "landing_page": landing_page,
                    "phone_number": phone_number,
                    "daily_budget_micro_amount": int(daily_budget_brl * 1_000_000), # Google Ads usa micro-unidades
                    "template_key": templates[template_selecionado]
                })
                
                # AQUI ENTRARÁ A LÓGICA PARA CHAMAR A API DO GOOGLE ADS
                # Por enquanto, apenas exibimos os dados.
