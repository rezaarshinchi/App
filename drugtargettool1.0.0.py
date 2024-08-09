import os
import sys
import pandas as pd
import random
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.scrolledtext import ScrolledText
from tkinter import ttk
from deap import base, creator, tools, algorithms
import warnings
import threading
import queue

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(__file__)
    return os.path.join(base_path, relative_path)

def load_data(file_path):
    """Load data from the selected file into a DataFrame."""
    if file_path.endswith('.csv'):
        return pd.read_csv(file_path)
    elif file_path.endswith('.xlsx'):
        return pd.read_excel(file_path)
    else:
        raise ValueError("Unsupported file format. Please choose a CSV or Excel file.")

def evaluate(individual, data, unique_targets):
    """Evaluate the fitness of an individual."""
    selected_drugs = [drug for i, drug in enumerate(data['Drug'].unique()) if individual[i] == 1]
    selected_targets = data[data['Drug'].isin(selected_drugs)]['Target'].unique()
    return len(selected_targets),

def update_progress(progress_var, progress_queue):
    """Update the progress bar based on progress_queue."""
    try:
        progress = progress_queue.get_nowait()
        if progress >= 0:  
            progress_var.set(progress)
            app.after(100, update_progress, progress_var, progress_queue)
    except queue.Empty:
        if progress_var.get() < 100:
            app.after(100, update_progress, progress_var, progress_queue)
        else:
            progress_var.set(100)  

def run_genetic_algorithm(file_path, num_top_drugs, progress_queue):
    global best_combinations
    
    try:
        data = load_data(file_path)
    except Exception as e:
        progress_queue.put(-1)
        messagebox.showerror("Error", f"Error loading file: {e}")
        return None
    
    if 'Target' not in data.columns or 'Drug' not in data.columns:
        progress_queue.put(-1)
        messagebox.showerror("Error", "The selected file must contain 'Target' and 'Drug' columns.")
        return None
    
    unique_targets = len(data['Target'].unique())
    num_drugs = len(data['Drug'].unique())


    random.seed(42)
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
        creator.create("Individual", list, fitness=creator.FitnessMax)
    
    toolbox = base.Toolbox()
    toolbox.register("attr_bool", random.randint, 0, 1)
    toolbox.register("individual", tools.initRepeat, creator.Individual, toolbox.attr_bool, n=num_drugs)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    
    toolbox.register("evaluate", evaluate, data=data, unique_targets=unique_targets)
    toolbox.register("mate", tools.cxTwoPoint)
    toolbox.register("mutate", tools.mutFlipBit, indpb=0.05)
    toolbox.register("select", tools.selTournament, tournsize=3)
    
    population = toolbox.population(n=300)
    num_generations = 40

    for gen in range(num_generations):
        algorithms.eaSimple(population, toolbox, cxpb=0.5, mutpb=0.2, ngen=1, verbose=False)
        progress = (gen + 1) / num_generations * 100
        progress_queue.put(progress)
    
    top_individuals = tools.selBest(population, k=num_top_drugs)
    
    drug_target_counts = {drug: len(data[data['Drug'] == drug]['Target'].unique()) for drug in data['Drug'].unique()}
    drug_targets = {drug: data[data['Drug'] == drug]['Target'].unique() for drug in data['Drug'].unique()}
    
    selected_drugs = []
    for individual in top_individuals:
        selected_drugs += [data['Drug'].unique()[i] for i in range(num_drugs) if individual[i] == 1]
    
    unique_selected_drugs = list(set(selected_drugs))
    unique_selected_drugs.sort(key=lambda drug: drug_target_counts[drug], reverse=True)
    
    result = []
    best_combinations = []
    result_list = []
    for drug in unique_selected_drugs[:num_top_drugs]:
        targets = drug_targets[drug]
        result.append(f"{drug} covers {len(targets)} targets: {', '.join(targets)}")
        best_combinations.append((drug, targets))
        result_list.append({'Drug': drug, 'Target Count': len(targets)})
    

    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
    result_file_path = os.path.join(desktop_path, "result.xlsx")
    result_df = pd.DataFrame(result_list)
    result_df.to_excel(result_file_path, index=False)
    
    progress_queue.put(100)  
    return result

def choose_file():
    global selected_file_path
    selected_file_path = filedialog.askopenfilename(
        title="Select Data File",
        filetypes=[("CSV and Excel files", "*.csv *.xlsx"), ("CSV files", "*.csv"), ("Excel files", "*.xlsx")]
    )
    if selected_file_path:
        file_label.config(text=f"Selected File: {os.path.basename(selected_file_path)}")
    else:
        file_label.config(text="No file selected")

def on_run():
    global selected_file_path
    if not selected_file_path:
        messagebox.showerror("Error", "No file selected.")
        return

    num_top_drugs = num_top_drugs_entry.get()

    if not num_top_drugs:
        messagebox.showerror("Error", "Enter the number of top drugs.")
        return

    try:
        num_top_drugs = int(num_top_drugs)
        if num_top_drugs <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Error", "Please enter a valid positive integer for the number of top drugs.")
        return

    progress_var.set(5)
    result_text.delete('1.0', tk.END)

    progress_queue = queue.Queue()

    progress_label = tk.Label(tab_drugcomga, text="Searching for the file...", bg="lightblue")
    progress_label.pack(pady=5)

    def run_genetic_algorithm_thread():
        progress_queue.put(10)

        progress_label.config(text="Running the algorithm...")

        result = run_genetic_algorithm(selected_file_path, num_top_drugs, progress_queue)
        if result:
            result_list = []
            for idx, line in enumerate(result, 1):
                drug_name, targets = line.split(' covers ')
                targets_list = targets.replace(': ', '').split(', ')
                for target in targets_list:
                    result_list.append({'Drug': drug_name.strip(), 'Target': target.strip()})
                result_text.insert(tk.END, f"{idx}- {line}\n\n", "bold")


            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            result_file_path = os.path.join(desktop_path, "result.xlsx")
            result_list = []

            for drug, targets in best_combinations:
                for target in targets:
                    result_list.append({'Drug': drug, 'Target': target})

 
            result_df = pd.DataFrame(result_list, columns=['Drug', 'Target'])
            result_df.to_excel(result_file_path, index=False)

            messagebox.showinfo("Success", f"Results saved to '{result_file_path}'.")

        progress_queue.put(100)

    threading.Thread(target=run_genetic_algorithm_thread, daemon=True).start()

    app.after(100, update_progress, progress_var, progress_queue)

    def update_label():
        try:
            progress = progress_queue.get_nowait()
            if progress < 100:
                if progress < 20:
                    progress_label.config(text="Searching for the file...")
                else:
                    progress_label.config(text="Running the algorithm...")
                app.after(100, update_label)
            else:
                progress_label.config(text="Completed!")
        except queue.Empty:
            app.after(100, update_label)

    app.after(100, update_label)

def run_combination_therapy():
    """Function to handle the combination therapy analysis."""
    if not best_combinations:
        result_text_combination.delete('1.0', tk.END)
        result_text_combination.insert(tk.END, "No combination therapy results available. Rrun the genetic algorithm first.", "bold")
        return
    

    combination_results = []
    
    for i in range(len(best_combinations) - 1):
        drug1, targets1 = best_combinations[i]
        for j in range(i + 1, len(best_combinations)):
            drug2, targets2 = best_combinations[j]
            shared_targets = set(targets1) & set(targets2)
            if shared_targets:
                combination_results.append((drug1, drug2, len(shared_targets), shared_targets))
    

    combination_results.sort(key=lambda x: x[2], reverse=True)
    
    result_text_combination.delete('1.0', tk.END)
    if combination_results:
        for drug1, drug2, shared_count, shared_targets in combination_results:
            result_text_combination.insert(tk.END, f"{drug1} and {drug2} collectively target: {', '.join(shared_targets)}\n\n", "bold")
    else:
        result_text_combination.insert(tk.END, "No significant combination found.", "bold")

app = tk.Tk()
app.title("DrugTargetTool 1.0.0")
app.geometry("800x600")
app.config(bg="lightblue")

app.iconbitmap('C:/Users/rarshinchibonab/Desktop/Python/DrugComGA/GAI.ico')


header_frame = tk.Frame(app, bg="lightblue")
header_frame.pack(fill=tk.X)

title_label = tk.Label(header_frame, text="Drug Combination  By Genetic Algorithm", bg="lightblue", font=("Helvetica", 12))
title_label.pack(side=tk.LEFT, padx=10)

developer_label = tk.Label(header_frame, text="Sadaf&Reza, Aug 2024", bg="lightblue", font=("Helvetica", 8))
developer_label.pack(side=tk.RIGHT, padx=10)

notebook = ttk.Notebook(app)
notebook.pack(pady=10, expand=True)

tab_drugcomga = ttk.Frame(notebook)
tab_combination = ttk.Frame(notebook)

notebook.add(tab_drugcomga, text='Top Drugs')
notebook.add(tab_combination, text='Combination Therapy')

selected_file_path = ""


instructions = """
Instructions:
1. Click 'Choose File' to select a CSV or Excel file containing 'Drug' and 'Target' columns.
2. Enter the number of top drugs to display.
3. Click 'Run' to start the genetic algorithm.
4. Results will be displayed and saved to your desktop as 'result.xlsx'.
"""
tk.Label(tab_drugcomga, text=instructions, bg="lightblue", justify=tk.LEFT).pack(pady=10)

file_label = tk.Label(tab_drugcomga, text="No file selected")
file_label.pack(pady=10)

choose_file_button = tk.Button(tab_drugcomga, text="Choose File", command=choose_file, bg="lightblue")
choose_file_button.pack(pady=5)

tk.Label(tab_drugcomga, text="Number of Top Drugs:").pack(pady=5)
num_top_drugs_entry = tk.Entry(tab_drugcomga)
num_top_drugs_entry.pack(pady=5)

progress_var = tk.DoubleVar()
progress_bar = ttk.Progressbar(tab_drugcomga, orient="horizontal", length=400, mode="determinate", variable=progress_var, maximum=100)
progress_bar.pack(pady=10)

run_button = tk.Button(tab_drugcomga, text="Run", command=on_run, bg="lightblue")
run_button.pack(pady=10)

result_text = ScrolledText(tab_drugcomga, width=80, height=20)
result_text.pack(pady=10)
result_text.tag_configure("bold", font=("Helvetica", 10, "bold"))

tk.Label(tab_combination, text="Combination Therapy Analysis").pack(pady=10)
run_combination_button = tk.Button(tab_combination, text="Run Combination Therapy", command=run_combination_therapy, bg="lightblue")
run_combination_button.pack(pady=10)

result_text_combination = ScrolledText(tab_combination, width=80, height=20)
result_text_combination.pack(pady=10)
result_text_combination.tag_configure("bold", font=("Helvetica", 10, "bold"))


app.mainloop()