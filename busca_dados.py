import requests
from bs4 import BeautifulSoup
import json
import re
import time

# --- CONFIGURAÇÕES ---
BASE_URL = "https://wol.jw.org"
URL_ANO_2026 = "https://wol.jw.org/pt/wol/library/r5/lp-t/todas-as-publicações/apostilas/apostila-vida-e-ministério-2026"

def extrair_dados_semana(url_semana):
    """Entra na página da semana e extrai as partes com sistema de retentativa"""
    tentativas = 3
    for i in range(tentativas):
        try:
            # Timeout de 30 segundos para evitar o erro de 'Read timed out'
            res = requests.get(url_semana, timeout=30)
            res.encoding = 'utf-8'
            soup = BeautifulSoup(res.text, 'html.parser')
            
            # O título da semana (ex: 5-11 de janeiro)
            semana_tag = soup.find('h1', id='p1')
            if not semana_tag:
                return None
            
            nome_semana = semana_tag.get_text(strip=True)
            
            # Filtro extra: ignora páginas da Celebração ou Memorial
            if "CELEBRAÇÃO" in nome_semana.upper() or "MEMORIAL" in nome_semana.upper():
                print(f"      ⏭️  Ignorando (Semana Especial): {nome_semana}")
                return None

            reuniao = {"semana": nome_semana, "secoes": []}
            secao_atual = None
            
            # Itera sobre os títulos h2 (seções) e h3 (partes)
            for el in soup.find_all(['h2', 'h3']):
                texto = el.get_text(" ", strip=True)
                
                # Identifica uma Seção (ex: Tesouros, Faça seu Melhor...)
                if el.name == 'h2' and "ISAÍAS" not in texto.upper():
                    secao_atual = {"titulo": texto, "partes": []}
                    reuniao["secoes"].append(secao_atual)
                
                # Identifica uma Parte (Tarefa)
                elif el.name == 'h3' and secao_atual:
                    texto_p = el.find_next('p').get_text() if el.find_next('p') else ""
                    busca_min = re.search(r'\((\d+)\s*min\)', texto + " " + texto_p)
                    tempo = int(busca_min.group(1)) if busca_min else 0
                    
                    secao_atual["partes"].append({
                        "titulo_parte": texto.split('(')[0].strip(),
                        "tempo": tempo,
                        "tem_contador": "Joias espirituais" in texto
                    })
            return reuniao

        except (requests.exceptions.RequestException, requests.exceptions.Timeout):
            print(f"      ⚠️  Timeout na tentativa {i+1}/{tentativas}. Tentando novamente...")
            time.sleep(3) # Espera 3 segundos antes de tentar de novo
            
    print(f"      ❌ Falha definitiva em: {url_semana}")
    return None

def iniciar_automacao():
    print("🚀 Iniciando robô rastreador (Versão Estabilizada)...")
    agenda_total = []
    
    # 1. Acessa o índice do ano
    try:
        res_ano = requests.get(URL_ANO_2026, timeout=30)
        soup_ano = BeautifulSoup(res_ano.text, 'html.parser')
    except Exception as e:
        print(f"❌ Erro fatal ao acessar o índice: {e}")
        return

    # 2. Encontra os links dos MESES
    links_meses = []
    for card in soup_ano.select('ul.directory li.row a'):
        href = card['href']
        if "/apostila-vida-e-ministério-2026/" in href:
            links_meses.append(BASE_URL + href)
    
    links_meses = list(dict.fromkeys(links_meses))
    print(f"📅 Meses encontrados: {len(links_meses)}")

    # 3. Entra em cada Mês
    for url_mes in links_meses:
        nome_mes = url_mes.split('/')[-1].upper()
        print(f"\n📂 Abrindo mês: {nome_mes}")
        
        try:
            res_mes = requests.get(url_mes, timeout=30)
            soup_mes = BeautifulSoup(res_mes.text, 'html.parser')
        except:
            print(f"   ❌ Não foi possível abrir o mês {nome_mes}")
            continue
        
        # 4. Busca os links das semanas pelo padrão de texto (tem número e não é capa)
        links_semanas = []
        for a_sem in soup_mes.select('ul.directory li.row a'):
            texto_link = a_sem.get_text(strip=True)
            href_sem = a_sem['href']
            
            contem_numero = any(char.isdigit() for char in texto_link)
            nao_e_capa = "Apostila da Reunião" not in texto_link
            
            if contem_numero and nao_e_capa:
                links_semanas.append(BASE_URL + href_sem)
        
        links_semanas = list(dict.fromkeys(links_semanas))
        print(f"   🔗 Encontrei {len(links_semanas)} links potenciais.")

        # 5. Extrai os dados
        for url_final in links_semanas:
            dados = extrair_dados_semana(url_final)
            if dados:
                print(f"      ✅ OK: {dados['semana']}")
                agenda_total.append(dados)
            # Pausa para evitar bloqueio do servidor
            time.sleep(1)

    # 6. Salva o resultado final
    if agenda_total:
        # Remove duplicatas por nome da semana
        vistos = set()
        agenda_limpa = []
        for item in agenda_total:
            if item['semana'] not in vistos:
                agenda_limpa.append(item)
                vistos.add(item['semana'])

        with open('agenda_2026.json', 'w', encoding='utf-8') as f:
            json.dump(agenda_limpa, f, indent=4, ensure_ascii=False)
        print(f"\n✨ SUCESSO! {len(agenda_limpa)} semanas salvas em 'agenda_2026.json'")
    else:
        print("\n❌ Nenhum dado foi extraído. O site pode estar instável.")

if __name__ == "__main__":
    iniciar_automacao()