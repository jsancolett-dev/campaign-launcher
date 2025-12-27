# app.py (CampaignLauncher v3.0 - Lógica da API do Google Ads)

import streamlit as st
import os
import uuid
from sqlalchemy import create_engine, text
import pandas as pd
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

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

# --- LÓGICA DO GOOGLE ADS ---

# Função para carregar as credenciais do Google Ads a partir das variáveis de ambiente
def get_google_ads_client():
    """
    Monta o dicionário de configuração e inicializa o cliente da API do Google Ads.
    """
    credentials = {
        "developer_token": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.environ.get("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.environ.get("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.environ.get("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": os.environ.get("GOOGLE_ADS_LOGIN_CUSTOMER_ID"),
        "use_proto_plus": "True",
    }
    # Verifica se todas as credenciais foram carregadas
    if not all(credentials.values()):
        st.error("Erro de Autenticação: Nem todas as variáveis de ambiente do Google Ads foram configuradas no Render.")
        st.stop()
        
    return GoogleAdsClient.load_from_dict(credentials)

# Função principal para criar a campanha
def create_campaign(google_ads_client, customer_id, campaign_data):
    """
    Orquestra a criação de uma campanha de pesquisa completa.
    """
    try:
        # Passo 1: Criar um Orçamento de Campanha
        budget_resource_name = _create_campaign_budget(google_ads_client, customer_id, campaign_data["daily_budget_micro_amount"])
        st.write(f"✅ Orçamento criado: {budget_resource_name}")

        # Passo 2: Criar a Campanha
        campaign_resource_name = _create_campaign(google_ads_client, customer_id, budget_resource_name, campaign_data["landing_page"])
        st.write(f"✅ Campanha criada: {campaign_resource_name}")

        # Passo 3: Criar o Grupo de Anúncios
        ad_group_resource_name = _create_ad_group(google_ads_client, customer_id, campaign_resource_name)
        st.write(f"✅ Grupo de Anúncios criado: {ad_group_resource_name}")

        # Passo 4: Criar as Palavras-chave
        keywords = campaign_data["keywords"] # Pega as palavras-chave do template
        _create_keywords(google_ads_client, customer_id, ad_group_resource_name, keywords)
        st.write(f"✅ {len(keywords)} Palavras-chave criadas.")

        # Passo 5: Criar o Anúncio Responsivo de Pesquisa (RSA)
        _create_responsive_search_ad(google_ads_client, customer_id, ad_group_resource_name, campaign_data["ad_headlines"], campaign_data["ad_descriptions"])
        st.write("✅ Anúncio de Pesquisa criado.")

        st.success("🎉 Campanha lançada com sucesso no Google Ads!")
        return True

    except GoogleAdsException as ex:
        st.error("Ocorreu um erro ao criar a campanha no Google Ads:")
        for error in ex.failure.errors:
            st.error(f'\tCódigo de Erro: {error.error_code}')
            st.error(f'\tMensagem: {error.message}')
        return False
    except Exception as e:
        st.error(f"Um erro inesperado ocorreu: {e}")
        return False

# Funções auxiliares (prefixadas com _)
def _create_campaign_budget(client, customer_id, budget_micro_amount):
    campaign_budget_service = client.get_service("CampaignBudgetService")
    campaign_budget_operation = client.get_type("CampaignBudgetOperation")
    campaign_budget = campaign_budget_operation.create
    campaign_budget.name = f"Orçamento Lançador #{uuid.uuid4()}"
    campaign_budget.delivery_method = client.get_type("BudgetDeliveryMethodEnum").BudgetDeliveryMethod.STANDARD
    campaign_budget.amount_micros = budget_micro_amount
    response = campaign_budget_service.mutate_campaign_budgets(customer_id=customer_id, operations=[campaign_budget_operation])
    return response.results[0].resource_name

def _create_campaign(client, customer_id, budget_resource_name, landing_page):
    campaign_service = client.get_service("CampaignService")
    campaign_operation = client.get_type("CampaignOperation")
    campaign = campaign_operation.create
    campaign.name = f"Campanha Lançador - Psicologia #{uuid.uuid4()}"
    campaign.advertising_channel_type = client.get_type("AdvertisingChannelTypeEnum").AdvertisingChannelType.SEARCH
    campaign.status = client.get_type("CampaignStatusEnum").CampaignStatus.PAUSED # Começa pausada por segurança
    campaign.manual_cpc.enhanced_cpc_enabled = True
    campaign.campaign_budget = budget_resource_name
    campaign.network_settings.target_google_search = True
    campaign.network_settings.target_search_network = True
    campaign.network_settings.target_content_network = False
    campaign.network_settings.target_partner_search_network = False
    campaign.final_url_suffix = f"utm_source=google&utm_medium=cpc&utm_campaign={campaign.name}"
    response = campaign_service.mutate_campaigns(customer_id=customer_id, operations=[campaign_operation])
    return response.results[0].resource_name

def _create_ad_group(client, customer_id, campaign_resource_name):
    ad_group_service = client.get_service("AdGroupService")
    ad_group_operation = client.get_type("AdGroupOperation")
    ad_group = ad_group_operation.create
    ad_group.name = "Grupo Principal - Psicologia"
    ad_group.status = client.get_type("AdGroupStatusEnum").AdGroupStatus.ENABLED
    ad_group.campaign = campaign_resource_name
    ad_group.type_ = client.get_type("AdGroupTypeEnum").AdGroupType.SEARCH_STANDARD
    response = ad_group_service.mutate_ad_groups(customer_id=customer_id, operations=[ad_group_operation])
    return response.results[0].resource_name

def _create_keywords(client, customer_id, ad_group_resource_name, keywords):
    ad_group_criterion_service = client.get_service("AdGroupCriterionService")
    operations = []
    for keyword in keywords:
        operation = client.get_type("AdGroupCriterionOperation")
        criterion = operation.create
        criterion.ad_group = ad_group_resource_name
        criterion.keyword.text = keyword
        criterion.keyword.match_type = client.get_type("KeywordMatchTypeEnum").KeywordMatchType.BROAD # ou PHRASE, EXACT
        operations.append(operation)
    ad_group_criterion_service.mutate_ad_group_criteria(customer_id=customer_id, operations=operations)

def _create_responsive_search_ad(client, customer_id, ad_group_resource_name, headlines, descriptions):
    ad_group_ad_service = client.get_service("AdGroupAdService")
    ad_group_ad_operation = client.get_type("AdGroupAdOperation")
    ad_group_ad = ad_group_ad_operation.create
    ad_group_ad.ad_group = ad_group_resource_name
    ad_group_ad.ad.final_urls.append("https://www.sitedocliente.com" ) # URL é obrigatória, mas será a da campanha
    
    # Títulos
    for text_ in headlines:
        ad_text_asset = client.get_type("AdTextAsset")
        ad_text_asset.text = text_
        ad_group_ad.ad.responsive_search_ad.headlines.append(ad_text_asset)
    # Descrições
    for text_ in descriptions:
        ad_text_asset = client.get_type("AdTextAsset")
        ad_text_asset.text = text_
        ad_group_ad.ad.responsive_search_ad.descriptions.append(ad_text_asset)
        
    ad_group_ad_service.mutate_ad_group_ads(customer_id=customer_id, operations=[ad_group_ad_operation])

# --- Funções de Interface ---
@st.cache_data(ttl=600)
def carregar_clientes():
    # ... (código sem alterações)
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
    st.warning("Nenhum cliente encontrado. Cadastre clientes no AgencyOS primeiro.")
    st.stop()

cliente_selecionado = st.selectbox("Selecione o cliente:", options=df_clientes['display_name'], index=None, placeholder="Escolha um cliente...")

if cliente_selecionado:
    st.success(f"Cliente selecionado: **{cliente_selecionado}**")
    st.markdown("---")
    
    st.header("2. Configurações da Campanha no Google Ads")
    with st.form("campaign_form"):
        customer_id = st.text_input("ID da Conta do Cliente no Google Ads*", placeholder="1234567890")
        landing_page = st.text_input("URL da Landing Page do Cliente*", placeholder="https://www.sitedopsicologo.com.br" )
        phone_number = st.text_input("Telefone para o Anúncio (WhatsApp)*", placeholder="5511999998888")
        daily_budget_brl = st.number_input("Orçamento Diário (R$)*", min_value=10.0, value=50.0, step=5.0)

        st.markdown("---")
        st.header("3. Seleção do Template de Anúncio")
        
        # Nossos templates de anúncio
        templates = {
            "Psicologia - Terapia de Ansiedade": {
                "headlines": ["Psicólogo para Ansiedade", "Terapia Online Disponível", "Agende sua Consulta Hoje"],
                "descriptions": ["Encontre ajuda profissional para lidar com a ansiedade.", "Sessões de terapia no conforto da sua casa."],
                "keywords": ["psicólogo para ansiedade", "terapia para ansiedade online", "tratamento ansiedade"]
            },
            "Psicologia - Terapia de Casal": {
                "headlines": ["Terapia de Casal Online", "Melhore seu Relacionamento", "Ajuda Profissional para Casais"],
                "descriptions": ["Resolva conflitos e fortaleça a conexão com seu parceiro.", "Sessões online com total discrição."],
                "keywords": ["terapia de casal", "psicólogo para casais", "terapia de relacionamento"]
            }
        }
        template_selecionado_nome = st.selectbox("Selecione o modelo de campanha:", options=templates.keys())

        submitted = st.form_submit_button("🚀 Lançar Campanha!")

        if submitted:
            if not all([customer_id, landing_page, phone_number, daily_budget_brl]):
                st.warning("Por favor, preencha todos os campos obrigatórios (*).")
            else:
                with st.spinner("Conectando ao Google Ads e criando campanha... Por favor, aguarde."):
                    # Prepara os dados para a função de criação
                    selected_template_data = templates[template_selecionado_nome]
                    campaign_data = {
                        "landing_page": landing_page,
                        "phone_number": phone_number,
                        "daily_budget_micro_amount": int(daily_budget_brl * 1_000_000),
                        "ad_headlines": selected_template_data["headlines"],
                        "ad_descriptions": selected_template_data["descriptions"],
                        "keywords": selected_template_data["keywords"]
                    }
                    
                    # Inicializa o cliente da API
                    google_ads_client = get_google_ads_client()
                    
                    # Chama a função principal de criação
                    create_campaign(google_ads_client, customer_id.replace("-", ""), campaign_data)

