# ProjectIA
 import tkinter as tk
from tkinter import scrolledtext
from tkinter import messagebox
import openai

# Configure sua chave de API da OpenAI
openai.api_key = "sua-chave-de-api-aqui"

def process_input():
    user_input = input_box.get("1.0", tk.END).strip()
    if user_input:
        # Chama a função para gerar uma resposta
        response = generate_response(user_input)
        output_box.config(state=tk.NORMAL)
        output_box.insert(tk.END, f"User: {user_input}\nAI: {response}\n\n")
        output_box.config(state=tk.DISABLED)
        input_box.delete("1.0", tk.END)
    else:
        messagebox.showwarning("Input Error", "Please enter some text.")

def limit_input(event):
    max_chars = 200  # Limite de caracteres
    current_text = input_box.get("1.0", tk.END)
    if len(current_text) > max_chars:
        input_box.delete(f"1.{max_chars}", tk.END)  # Remove o excesso
        messagebox.showwarning("Input Limit", f"Maximum {max_chars} characters allowed.")

def generate_response(user_input):
    try:
        # Chamada à API do ChatGPT
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Modelo do ChatGPT
            messages=[
                {"role": "system", "content": "Você é um assistente útil."},
                {"role": "user", "content": user_input}
            ]
        )
        # Retorna a resposta gerada pela IA
        return response['choices'][0]['message']['content'].strip()
    except openai.error.AuthenticationError:
        return "Erro de autenticação: verifique sua chave de API."
    except openai.error.APIConnectionError:
        return "Erro de conexão: verifique sua conexão com a internet."
    except Exception as e:
        return f"Erro ao se comunicar com a API: {e}"

# Create main window
root = tk.Tk()
root.title("AI Functional Interface")
root.geometry("600x400")

# Input box
input_label = tk.Label(root, text="Enter your input:")
input_label.pack(pady=5)
input_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=5)
input_box.pack(pady=5)

# Vincular o evento ao widget de entrada
input_box.bind("<KeyRelease>", limit_input)

# Submit button
submit_button = tk.Button(root, text="Submit", command=process_input)
submit_button.pack(pady=5)

# Output box
output_label = tk.Label(root, text="AI Output:")
output_label.pack(pady=5)
output_box = scrolledtext.ScrolledText(root, wrap=tk.WORD, height=10, state=tk.DISABLED)
output_box.pack(pady=5)

# Run the application
root.mainloop()
