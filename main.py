import json
import time
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import base64
from playwright.sync_api import sync_playwright

# Logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S'
)
logger = logging.getLogger(__name__)


def extrair_dados(page):
    logger.info("Extraindo dados meteorológicos da página...")
    data_infos = page.query_selector('.calendar').get_attribute('data-infos')
    dados = json.loads(data_infos)
    lista = []
    for dia in dados:
        lista.append({
            'data': dia.get('date'),
            'min': dia.get('temperature', {}).get('min'),
            'max': dia.get('temperature', {}).get('max'),
            'descricao': dia.get('textIcon', {}).get('text', {}).get('pt', '')
        })
    logger.info(f"Extraídos dados para {len(lista)} dias.")
    return lista


def criar_grafico(dados_15):
    logger.info("Criando gráfico de temperaturas...")
    df_dados = []
    for d in dados_15:
        data_formatada = datetime.strptime(d['data'], '%Y-%m-%d')
        df_dados.append({
            'Data': data_formatada,
            'Mínima': d['min'],
            'Máxima': d['max']
        })

    df = pd.DataFrame(df_dados)

    plt.figure(figsize=(14, 7))
    plt.plot(df['Data'], df['Mínima'], marker='o', linewidth=2, label='Temperatura Mínima', color='blue')
    plt.plot(df['Data'], df['Máxima'], marker='s', linewidth=2, label='Temperatura Máxima', color='red')

    plt.title('Previsão de Temperaturas - Curitiba - 15 Dias', fontsize=16, fontweight='bold')
    plt.xlabel('Data', fontsize=12)
    plt.ylabel('Temperatura (°C)', fontsize=12)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)

    plt.gca().xaxis.set_major_locator(mdates.DayLocator())
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
    plt.xticks(df['Data'], rotation=45)

    plt.tight_layout()

    img_path = Path.cwd() / 'temp_grafico.png'
    plt.savefig(img_path, dpi=300, bbox_inches='tight')
    plt.close()
    logger.info(f"Gráfico salvo em {img_path}")
    return img_path


def criar_pagina_html(dados_15, img_path, caminho_html):  
    logger.info("Gerando página HTML com dados e gráfico...")  
    # codifica imagem em base64  
    with open(img_path, 'rb') as f:  
        img_b64 = base64.b64encode(f.read()).decode()  
  
    # Monta tabela HTML  
    linhas = []  
    for d in dados_15:  
        data_formatada = datetime.strptime(d['data'], '%Y-%m-%d').strftime('%d/%m/%Y')  
        linhas.append(f"<tr><td>{data_formatada}</td><td>{d['min']}</td><td>{d['max']}</td><td>{d['descricao']}</td></tr>")  
  
    tabela_html = """  
    <table border="1" cellpadding="6" cellspacing="0">  
      <thead>  
        <tr><th>Data</th><th>Mínima (°C)</th><th>Máxima (°C)</th><th>Descrição</th></tr>  
      </thead>  
      <tbody>  
        {rows}  
      </tbody>  
    </table>  
    """.format(rows="\n".join(linhas))  
  
    # Usando f-string corretamente com tabela_html  
    html = f"""  
    <!doctype html>  
    <html lang="pt-BR">  
    <head>  
      <meta charset="utf-8"/>  
      <meta name="viewport" content="width=device-width,initial-scale=1"/>  
      <title>Previsão Curitiba - 15 dias</title>  
      <style>  
        body {{ font-family: Arial, sans-serif; margin: 20px; }}  
        h1 {{ color: #333; }}  
        table {{ border-collapse: collapse; margin-top: 20px; width: 100%; max-width: 900px; }}  
        th {{ background: #f0f0f0; }}  
        img {{ max-width: 100%; height: auto; margin-top: 20px; }}  
      </style>  
    </head>  
    <body>  
      <h1>Previsão de Temperaturas - Curitiba (15 dias)</h1>  
      {tabela_html}  
      <div>  
        <h2>Gráfico</h2>  
        <img src="data:image/png;base64,{img_b64}" alt="Gráfico de temperaturas"/>  
      </div>  
      <footer><small>Atualizado em {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</small></footer>  
    </body>  
    </html>  
    """

    caminho_html.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho_html, 'w', encoding='utf-8') as f:
        f.write(html)

    logger.info(f"Página HTML salva em {caminho_html}")


def rodar():
    logger.info("Iniciando processo de coleta e geração de página...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto('https://www.climatempo.com.br/previsao-do-tempo/15-dias/cidade/271/curitiba-pr')

            page.click('#Botao_1_mais_5_dias_timeline_15_dias')
            time.sleep(1)

            dados_15 = extrair_dados(page)
            img_path = criar_grafico(dados_15)

            caminho_html = Path.cwd() / 'docs' / 'index.html'   # arquivo HTML gerado no repositório
            criar_pagina_html(dados_15, img_path, caminho_html)

            # remove arquivo temporário do gráfico
            try:
                img_path.unlink()
            except Exception:
                pass

            logger.info("Processo concluído com sucesso.")
            browser.close()
    except Exception as e:
        logger.error(f"Erro durante o processo: {e}", exc_info=True)


def loop_consultas():
    logger.info("Iniciando loop de consultas a cada 24 horas...")
    while True:
        try:
            rodar()
            time.sleep(86400)
        except KeyboardInterrupt:
            logger.info("Execução interrompida pelo usuário.")
            sys.exit(0)


if __name__ == "__main__":  
    if os.getenv("RUN_ONCE", "false").lower() in ("1", "true", "yes"):  
        rodar()
