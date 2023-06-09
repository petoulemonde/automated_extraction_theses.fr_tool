from tkinter import *
import tkinter as tk
from tkinter import simpledialog
from tkinter import messagebox

import pandas as pd
import os
import re
from unidecode import unidecode
import openpyxl

from bs4 import BeautifulSoup
import requests

from typing import List

from datetime import datetime

import pickle

def user_input_parsing(input_user) : 
    input_list = input_user.split(";")
    mask = []

    for count, element in enumerate(input_list) : 
        print("element n°", count+1, " on ", len(input_list))
        element = re.sub(' +', ' ', element) # Delete multiple spaces
        element = re.sub('^ +', '', element) # Delete spaces before reseach
        element = re.sub(' +$', '', element) # Delete spaces after reseach
        element = re.sub(' ', '+', element)
        element = unidecode(element) # delete accent
        
        print("element : '" + element + "'")
        
        if len(element) == 0 :
            print("1 element deleted because containing nothing")
        else : 
            mask = mask + [element]

    input_list = mask

    # Verifying output
    # print("Liste finale : ")
    print("Final list of elements: ",str(input_list))

    return input_list

def scraping_number_results(url_short) :
  url_short = url_short

  # Number of results
  html = requests.get(url_short)
  soup = BeautifulSoup(html.content, "html.parser")
  number_results = int(soup.find("div", attrs={"id":"resumR"}).find("span", attrs={"id":"sNbRes"}).text)

  return number_results

def result_scraping(n_res, url, element) :
  url = url
  number_results = n_res
  
  # Variables
  df_temp = pd.DataFrame()
  definitive_df  = pd.DataFrame()

  # Loop extraction
  start = 0
  number_results_loop = number_results

  while number_results_loop >= 0 :
    number_results_loop -= 1000
    # print("url : " + str(url.format(start)))
    print("For element : " + element + ", extraction from " + str(start) + " to " + str(min(number_results, start+1000)))
    df_temp = pd.read_csv(url.format(start), sep = ";")

    definitive_df = pd.concat([definitive_df, df_temp], ignore_index = True)
    
    start += 1000

  # inital : df = pd.read_csv(url)
  # pb : si plus de 1000 résultats, csv ne charge que les 1000 premeirs résultats
  return definitive_df

# input_list = ["transformation+chimique", "pathologie+digestive+numerique"] # input list for testing

def core_scrap(input_list) : 
  thesis_df_temp = []
  thesis_df = pd.DataFrame(columns = ['keywords', 'id_thesis'])

  robots_df = pd.read_csv("https://www.theses.fr/robots.txt", sep = ": ").rename(columns = {"User-agent":"col", "*":"id_thesis"})
  robots_df = robots_df[ (robots_df["col"] != "Crawl-delay") & (robots_df["col"] != "Sitemap") ] # Delete Site map and Crawl-delay rows
  illegal_url_list = robots_df.id_thesis.apply(lambda x: "https://www.theses.fr"+x).tolist() # List of disallow URL

  for element in input_list : 
    print("\n-------------------------------------------------")
    print("Element : " + element)

    # Recover previous researches results 
    try : 
      seen_df = pd.read_csv(element + ".csv")["seen_id_thesis"].tolist()
      print("File from previous researches found.\n")

      print("Number of thesis already seen in preceent researches : " + str(len(seen_df)))
    except : 
      print("This request has no precedent.\n")
      seen_df = []
    
    # Verifying number of results
    try : 
      number_results = scraping_number_results("https://www.theses.fr/?q=" + element)
      print(number_results, " results for element : ", element)
    except : 
      number_results = 0
      print("No results for this element : " + str(element))

    # Extract results
    if (number_results > 0) : 
      try : 
        # scrap_results = result_scraping(number_results, "https://www.theses.fr/?q=" + element + "&fq=dateSoutenance:[1965-01-01T23:59:59Z%2BTO%2B""extract_['transformation+chimique', 'pathologie+digestive+numerique']_2023-06-08.xlsx"+ 
        # datetime.now().strftime("%Y-%m-%d") + "T" + datetime.now().strftime("%H:%M:%S") + "Z" + 
        # "]&checkedfacets=&start={}&sort=none&status=&access=&prevision=&filtrepersonne=&zone1=titreRAs&val1=&op1=AND&zone2=auteurs&val2=&op2=AND&zone3=etabSoutenances&val3=&op3=AND&zone4=dateSoutenance&val4a=&val4b=&type=&lng=fr/&checkedfacets=&format=csv")
        
        scrap_results = result_scraping( number_results,
          "https://www.theses.fr/?q="+ element + 
          "&fq=dateSoutenance:[1965-01-01T23:59:59Z%2BTO%2B2023-12-31T23:59:59Z]&checkedfacets=&start={}&sort=none&status=&access=&prevision=&filtrepersonne=&zone1=titreRAs&val1=&op1=AND&zone2=auteurs&val2=&op2=AND&zone3=etabSoutenances&val3=&op3=AND&zone4=dateSoutenance&val4a=&val4b=&type=&lng=fr/&checkedfacets=&format=csv", 
          element  )
        
        scrap_results = scrap_results[["Statut", "Identifiant de la these", "Accessible en ligne", "Titre", "Auteur", "Directeur de these (nom prenom)", "Etablissement de soutenance", "Discipline"]]
        scrap_results["Identifiant de la these"] = scrap_results["Identifiant de la these"].apply(lambda x : "https://www.theses.fr/" + x)
        
        seen_precedent_researches = 0
        illegal_thesis = 0
        redundant_thesis = 0
        
        for id_thesis in scrap_results["Identifiant de la these"] : 
          # print("ID thesis evaluate : " + id_thesis)
          
          if id_thesis in seen_df : 
            seen_precedent_researches += 1
          else : 
            seen_df = seen_df + [id_thesis]
            if id_thesis in illegal_url_list :
              illegal_thesis += 1
            else : 
              if id_thesis in thesis_df_temp :
                redundant_thesis += 1
              else : 
                thesis_df_temp = thesis_df_temp + [id_thesis]
        
        # Save already seen thesis
        pd.DataFrame(seen_df, columns = ["seen_id_thesis"]).to_csv(str(element) + ".csv", index = False)
        
        # unser search results
        thesis_df = pd.concat([thesis_df,  
                              pd.DataFrame({'keywords':element, 'id_thesis':thesis_df_temp}).merge(scrap_results.rename(columns = {"Identifiant de la these":"id_thesis"}), 
                                                                                  on="id_thesis", 
                                                                                  how = "left")],
                              ignore_index = True)
        print("Thesis already seen in precedent researches : " + str(seen_precedent_researches))
        print("duplicate : " + str(redundant_thesis))
        print("Disallow thesis : " + str(illegal_thesis))
        print("Extraction from " + str(element) + " finished! ")

        print("Export OK")

      except : 
        print("Error in element : ", element)  

  # Save new thesis extracted
  thesis_df.to_excel("extract_" + str(input_list) + "_" + str(datetime.now())[:19].replace(":", "-") + ".xlsx", sheet_name = "extraction", index = False)
  # thesis_df.to_csv("extract_" + str(input_list) + "_" + str(datetime.now())[:10] + ".csv", index = False)

  print("\n---------------------------\nExecution finished !")

explanation_text  = "Cette application a pour but de vous aider à faire votre veille stratégique sur le site https://www.theses.fr. \n\n" +\
"Pour celà, voici les étapes : \n" +\
"1. Sélectionner les mots-clés que vous souhaitez rechercher. \n Vous pouvez entrez plusieurs mots-clés si vous les séparez par un point-virgule (;).\n" +\
"2. Cliquez sur le bouton 'Rechercher' pour lancer la recherche. \n\n" +\
"Les tips : \n" +\
"- les theses récupérées lors d'anciennes recherches ne ressortiront pas dans la recherche lancée et les futures recherches.\n" +\
"Vous pouvez supprimer l'historique des recherches en entrant les mots-clés souhaitées et en cliquant sur 'Supprimer l'historique'. \n" +\
"ATTENTION : pour supprimer l'historique, 1 seul mot clé à la fois !\n" +\
"- pour quitter l'application, cliquez sur le bouton 'Quitter'"

# Tkinter app
root = tk.Tk()
root.title("Veille stratégique theses.fr")
root.geometry('1000x500')

# ---- Etape 0 : Présentation
lbl_title_0 = Label(root, text = "Etape 0 : Présentation du projet", justify = LEFT)
lbl_title_0.config(font=("Courier", 12))
lbl_title_0.grid(column = 0, row = 0)

# ---- Explanation texts
lbl = Label(root, text = explanation_text, justify = LEFT)
lbl.grid(column = 0, row = 1, columnspan = 4)

# ---- Etape 1 : les mots clés
lbl_title_1 = Label(root, text = "Etape 1 : saisie des mots de recherche", justify = LEFT)
lbl_title_1.config(font=("Courier", 12))
lbl_title_1.grid(column = 0, row = 2)

# --- input_user entry zone
input_user = Entry(root, width = 100)
input_user.grid(column = 0, row = 3, sticky="w")

def clicked():
   user_input = user_input_parsing(input_user.get())
   with open("user_input.pickle", "wb") as fp:   #Pickling
      pickle.dump(user_input, fp)

   res = "Votre saisie : " + input_user.get()
   lbl_user_input.configure(text = res)

btn = Button(root, text = "Valider votre saisie" , command=clicked)
btn.grid(column = 2, row = 3)

# ---- Print user input
lbl_user_input = Label(root, text="", justify = LEFT)
lbl_user_input.grid(column=0, row = 4)

# ---- Choix des actions
lbl_title_2 = Label(root, text = "Etape 2 : les actions", justify = LEFT)
lbl_title_2.config(font=("Courier", 12))
lbl_title_2.grid(column = 0, row = 5)

# ---- lancer la recherche
def launch_scrap() :
   with open("user_input.pickle", "rb") as fp:   # Unpickling
      input_list = pickle.load(fp)

   core_scrap(input_list)

btn_scrap = Button(root, text = "lancer le scraping" , command=launch_scrap)
btn_scrap.grid(column = 0, row = 6)

# ---- Supprimer son historique
def delete_historic() :
   print("delete hisotric launch")
   
   with open("user_input.pickle", "rb") as fp:   # Unpickling
      user_input = pickle.load(fp)

   for element in user_input :
      print(element)
      try :
         os.remove(element + ".csv")
         print("found and delete")
      except : 
         print("unfound")
         
btn_hist = Button(root, text = "Supprimer historique" , command=delete_historic)
btn_hist.grid(column = 2, row = 6)

# ---- Conclusion
lbl_title_3 = Label(root, text = "Etape 3 : avant de partir", justify = LEFT)
lbl_title_3.config(font=("Courier", 12))
lbl_title_3.grid(column = 0, row = 7)

lbl_con = Label(root, text = "Quittez la fenetre pour quitter le programme.\n" + 
"Les résultats des extractions se trouveront dans le dossier ou se trouve le script python.", justify = LEFT)
lbl_con.grid(column = 0, row = 8)

# ---- Main loop
root.mainloop()

os.remove("user_input.pickle")

