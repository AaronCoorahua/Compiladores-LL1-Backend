import re

class Rule:
    def __init__(self, left, right):
        self.left = left
        self.right = right

    def __repr__(self):
        return f"{self.left} → {' '.join(self.right)}"


class Symbol:
    def __init__(self, value):
        self.value = value


class Terminal(Symbol):
    def __init__(self, value):
        super().__init__(value)
        self.first = {value}  # FIRST de un terminal es él mismo


class NonTerminal(Symbol):
    def __init__(self, value):
        super().__init__(value)
        self.first = set()
        self.follow = set()
        self.productions = []
        self.is_start = False


class Grammar:
    def __init__(self):
        self.terminals = {}
        self.non_terminals = {}
        self.start_symbol = None
        self.rules = []
        self.table = {}

    def load_from_string(self, content: str):
        lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
        # El primer carácter de la primera línea es símbolo inicial
        lhs0 = lines[0].split("->", 1)[0].strip()
        self.start_symbol = lhs0

        for line in lines:
            parts = line.split("->")
            if len(parts) != 2:
                continue
            left = parts[0].strip()
            right = parts[1].strip()

            # 1) dividir alternativas por '|'
            alts = [alt.strip() for alt in right.split('|')]

            # 2) procesar cada alternativa por separado
            for alt in alts:
                symbols = alt.split() if alt != '_' else ['_']
                # guardamos la Regla
                self.rules.append(Rule(left, symbols))

                # registramos el no-terminal
                if left not in self.non_terminals:
                    self.non_terminals[left] = NonTerminal(left)
                # añadimos la producción
                self.non_terminals[left].productions.append(symbols)

                # registrar símbolos terminales y no terminales
                for sym in symbols:
                    if sym == '_':  # ε
                        continue
                    if sym.isupper():
                        if sym not in self.non_terminals:
                            self.non_terminals[sym] = NonTerminal(sym)
                    else:
                        if sym not in self.terminals:
                            self.terminals[sym] = Terminal(sym)

        # Añadimos '$'
        self.terminals['$'] = Terminal('$')
        # Marcamos el inicio y su follow
        self.non_terminals[self.start_symbol].is_start = True
        self.non_terminals[self.start_symbol].follow.add('$')


    def load_from_file(self, filename):
        with open(filename, 'r') as f:
            lines = [line.strip() for line in f.readlines() if line.strip()]

        self.start_symbol = lines[0][0]

        for line in lines:
            parts = line.split("->")
            if len(parts) != 2:
                continue
            left = parts[0].strip()
            right = parts[1].strip()
            symbols = right.split() if right != '_' else ['_']

            self.rules.append(Rule(left, symbols))

            if left not in self.non_terminals:
                self.non_terminals[left] = NonTerminal(left)

            self.non_terminals[left].productions.append(symbols)

            for symbol in symbols:
                if symbol == '_':
                    continue
                if symbol.isupper():
                    if symbol not in self.non_terminals:
                        self.non_terminals[symbol] = NonTerminal(symbol)
                else:
                    if symbol not in self.terminals:
                        self.terminals[symbol] = Terminal(symbol)

        self.terminals['$'] = Terminal('$')
        self.non_terminals[self.start_symbol].is_start = True
        self.non_terminals[self.start_symbol].follow.add('$')

    def compute_first(self):


        changed = True  # Controla si hubo cambios para seguir iterando
        while changed:
            changed = False
            #print("rules:",self.rules)
            for rule in self.rules:
                left = rule.left  # No terminal izquierdo de la regla
                right = rule.right  # Parte derecha de la producción
                nt = self.non_terminals[left]  # Objeto NoTerminal correspondiente
                current_first = nt.first.copy()  # Copia actual de FIRST(A)
                #print("nt: ",nt.first)
                #print("current_first: ",current_first)
                nullable = True  # Asume que la producción podría derivar a ε

                for symbol in right:
                    if symbol == '_':
                        # Caso 1: La producción es A → ε
                        current_first.add('_')  # Añadir ε al FIRST
                        nullable = True  # No seguir revisando símbolos
                        break
                    elif symbol in self.non_terminals:
                        # Caso 2: El símbolo es un no terminal
                        # Añadir FIRST(symbol) menos ε
                        current_first |= (self.non_terminals[symbol].first ) # union sin repetidos
                        if '_' not in self.non_terminals[symbol].first:
                            # Si el símbolo no puede derivar ε, terminamos
                            nullable = False
                            break
                        # Si puede derivar ε, seguimos al siguiente símbolo
                    elif symbol in self.terminals:
                        # Caso 3: El símbolo es un terminal
                        current_first.add(symbol)  # Se agrega directamente al FIRST
                        nullable = False
                        break

                if nullable:
                    # Si todos los símbolos pueden derivar ε, se agrega ε
                    current_first.add('_')

                if current_first != nt.first:
                    # Si hubo cambios, actualizamos y marcamos cambio
                    nt.first = current_first
                    changed = True



    def compute_follow(self):
        changed = True
        while changed:
            changed = False
            for rule in self.rules:
                left = rule.left
                right = rule.right
                follow_temp = self.non_terminals[left].follow.copy()

                for i in reversed(range(len(right))):
                    symbol = right[i]
                    if symbol in self.non_terminals:
                        nt = self.non_terminals[symbol]
                        if not follow_temp.issubset(nt.follow):
                            nt.follow |= follow_temp
                            changed = True
                        if '_' in self.non_terminals[symbol].first:
                            follow_temp |= (self.non_terminals[symbol].first - {'_'})
                        else:
                            follow_temp = self.non_terminals[symbol].first
                    elif symbol != '_':
                        follow_temp = {symbol}

    def build_ll1_table(self):
        for nt in self.non_terminals:
            self.table[nt] = {t: [] for t in self.terminals}

        for rule in self.rules:
            left = rule.left
            right = rule.right
            first_alpha = set()
            nullable = True

            # Calcular FIRST(right) y si la producción es nullable
            for symbol in right:
                if symbol == '_':
                    break  # Producción explícitamente ε
                elif symbol in self.non_terminals:
                    first_alpha |= (self.non_terminals[symbol].first - {'_'})
                    if '_' not in self.non_terminals[symbol].first:
                        nullable = False
                        break
                else:
                    first_alpha.add(symbol)
                    nullable = False
                    break

            # Paso 1: Añadir a los terminales en FIRST(right)
            for terminal in first_alpha:
                self.table[left][terminal].append(rule)

            # Paso 2: Si la producción puede ser nullable, añadir a FOLLOW(left)
            if nullable or right == ['_']:
                for terminal in self.non_terminals[left].follow:
                    self.table[left][terminal].append(rule)

        self.apply_extrac()
        self.apply_explore()



    def apply_extrac(self):
        """Marca con 'explore' SOLO si la casilla está VACÍA y pertenece a FOLLOW o $."""
        for nt in self.non_terminals:
            for terminal in self.terminals:
                # Condiciones para marcar 'explore':
                # 1. La casilla NO tiene reglas (está vacía)
                # 2. El terminal está en FOLLOW(nt) o es $
                if (
                        not self.table[nt][terminal]  # Verifica que esté vacía
                        and (terminal in self.non_terminals[nt].follow or terminal == '$')
                ):
                    self.table[nt][terminal] = ["extrac"]
    def apply_explore(self):
        """Marca con 'explore' SOLO si la casilla está VACÍA y pertenece a FOLLOW o $."""
        for nt in self.non_terminals:
            for terminal in self.terminals:
                # Condiciones para marcar 'explore':
                # 1. La casilla NO tiene reglas (está vacía)
                # 2. El terminal está en FOLLOW(nt) o es $
                if(not self.table[nt][terminal]  ):
                    self.table[nt][terminal] = ["explore"]
    def print_first_follow(self):
        print(f"{'Símbolo':<10} {'FIRST':<20} {'FOLLOW':<20}")
        print("-" * 50)
        for symbol, nt in self.non_terminals.items():
            first = ', '.join(nt.first)
            follow = ', '.join(nt.follow)
            print(f"{symbol:<10} {first:<20} {follow:<20}")

    def print_table(self):
        print("\nTABLA LL(1):")
        print(f"{'':15}" + ''.join([f"{t:<15}" for t in self.terminals]))
        print("-" * (15 + 15 * len(self.terminals)))
        for nt in self.non_terminals:
            print(f"{nt:<15}", end='')
            for t in self.terminals:
                rules = self.table[nt][t]
                if rules:
                    print(f"{' / '.join(str(r) for r in rules):<15}", end='')
                else:
                    print(f"{'-':<15}", end='')
            print()
    def gramar_is_ll1(self):
        for nt in self.non_terminals:
            row = self.table[nt]
            for terminal, rules in row.items():
                if len(rules) > 1:
                    print(f"Conflicto en tabla LL(1) en M[{nt}][{terminal}]: {rules}")
                    return False
        return True

    def parse_2(self, input_string: str, max_steps: int):
        stack          = [('$', None), (self.start_symbol, None)]  
        input_tokens   = input_string.strip().split() + ['$']
        input_ptr      = 0

        trace          = []
        root           = {"label": self.start_symbol, "children": []}
        step_count     = 0

        used_explore   = False
        used_extract   = False
        explore_points = []      
        extract_points = []      

        while stack:
            step_count += 1
            if step_count > max_steps + 1:
                trace.append({
                    "stack": [sym for sym, _ in stack],
                    "input": input_tokens[input_ptr:],
                    "rule" : f"Error: Max‑steps limit ({max_steps})"
                })
                break

            top_symbol, parent = stack.pop()
            current_tok = input_tokens[input_ptr] if input_ptr < len(input_tokens) else '$'

            trace.append({
                "stack": [sym for sym, _ in stack] + [top_symbol],
                "input": input_tokens[input_ptr:],
                "rule" : ""
            })

            if top_symbol == '$' and current_tok == '$':
                trace[-1]["rule"] = "accept"
                break

            if top_symbol in self.terminals or top_symbol == '$':
                if top_symbol == current_tok:
                    trace[-1]["rule"] = f"match '{top_symbol}'"
                    input_ptr += 1
                    if parent is not None:
                        parent["children"].append({"label": top_symbol})
                else:
                    trace[-1]["rule"] = (
                        f"Error: se esperaba '{top_symbol}', "
                        f"pero se encontró '{current_tok}'"
                    )
                continue       # siguiente iteración

            if top_symbol in self.non_terminals:
                cell = self.table[top_symbol].get(current_tok, [])

                if cell and isinstance(cell[0], str) and cell[0] == "explore":
                    used_explore = True
                    explore_points.append({
                        "step"        : step_count,
                        "token"       : current_tok,
                        "non_terminal": top_symbol,
                    })
                    trace[-1]["rule"] = f"skip '{current_tok}' (explore)"
                    input_ptr += 1                  # descarta token
                    stack.append((top_symbol, parent)) 
                    continue

                if cell and isinstance(cell[0], str) and cell[0] == "extrac":
                    used_extract = True
                    extract_points.append({
                        "step"        : step_count,
                        "token"       : current_tok,
                        "non_terminal": top_symbol,
                    })
                    trace[-1]["rule"] = f"sync‑pop {top_symbol} (extract)"
                    continue          

                if not cell or not isinstance(cell[0], Rule):
                    trace[-1]["rule"] = (
                        f"Error: sin producción para {top_symbol} con '{current_tok}'"
                    )
                    break

                rule = cell[0]
                trace[-1]["rule"] = f"{rule.left} -> {' '.join(rule.right)}"

                node = {"label": top_symbol, "children": []}
                if parent is not None:
                    parent["children"].append(node)
                else:
                    root = node

                if rule.right != ['_']:                 # no ε
                    for sym in reversed(rule.right):
                        stack.append((sym, node))
                else:
                    node["children"].append({"label": "ε"})
                continue

            trace[-1]["rule"] = f"Error: símbolo desconocido '{top_symbol}'"
            break

        accepted = (
            trace and trace[-1]["rule"] == "accept"
            and not used_explore
            and not used_extract
        )

        return {
            "trace"          : trace,
            "tree"           : root,
            "explore_points" : explore_points,
            "extract_points" : extract_points,
            "accepted"       : accepted,
        }

    
    def parse(self, input_string):
        """
        Realiza el análisis sintáctico de una cadena y genera la tabla de derivación.
        """
        # Inicialización
        stack = ['$', self.start_symbol]
        input_string = input_string.split() + ['$']
        current_input = input_string.copy()
        steps = []
        step_count = 0

        # Configurar impresión bonita para producciones
        def format_production(rule):
            return f"{rule.left} → {' '.join(rule.right)}" if rule else ''

        while len(stack) > 0:
            step_count += 1
            top = stack[-1]
            current_token = current_input[0] if current_input else '$'

            # Registro del paso actual
            step = {
                'step': step_count,
                'stack': ' '.join(stack),
                'input': ' '.join(current_input),
                'action': ''
            }

            if top == '$' and current_token == '$':
                step['action'] = 'Aceptar'
                steps.append(step)
                break
            elif top == current_token:
                step['action'] = f'Desplazar {current_token}'
                stack.pop()
                current_input.pop(0)
                steps.append(step)
                continue
            elif top in self.terminals:
                step['action'] = f'Error: terminal inesperado {top}'
                steps.append(step)
                break
            elif top in self.non_terminals:
                productions = self.table[top].get(current_token, [])
                if not productions:
                    step['action'] = f'Error: No hay producción para {top} con {current_token}'
                    steps.append(step)
                    break

                if len(productions) > 1:
                    step['action'] = 'Error: Gramática no LL(1) - conflicto'
                    steps.append(step)
                    break

                production = productions[0]
                if isinstance(production, Rule):
                    step['action'] = format_production(production)
                    stack.pop()
                    if production.right[0] != '_':
                        for symbol in reversed(production.right):
                            stack.append(symbol)
                else:
                    step['action'] = f'Error: entrada inválida en la tabla LL(1): {production}'
                    steps.append(step)
                    break

                steps.append(step)
            else:
                step['action'] = 'Error desconocido'
                steps.append(step)
                break

        # Generar tabla de derivación
        print("\nTABLA DE DERIVACIÓN:")
        print(f"{'Paso':<5} {'Pila':<20} {'Entrada':<20} {'Acción':<30}")
        print("-" * 60)
        for step in steps:
            print(f"{step['step']:<5} {step['stack']:<20} {step['input']:<20} {step['action']:<30}")

        return steps[-1]['action'] == 'Aceptar'

    def is_ll1(self):
        """
        Verifica si la gramática es LL(1) mediante dos condiciones:
        1. Para cada no terminal con múltiples producciones, los FIRST deben ser disjuntos
        2. Para producciones que derivan ε, FIRST y FOLLOW deben ser disjuntos
        Retorna: (bool, dict) donde el dict contiene los conflictos encontrados
        """
        conflicts = {
            'first_conflicts': {},
            'follow_conflicts': {}
        }
        is_valid = True

        # Condición 1: Verificar FIRST disjuntos para producciones alternativas
        for nt in self.non_terminals.values():
            productions = nt.productions
            if len(productions) < 2:
                continue

            # Crear un diccionario de FIRST por producción
            first_sets = {}
            for prod in productions:
                first = set()
                nullable = True

                for symbol in prod:
                    if symbol == '_':
                        first.add('_')
                        break
                    elif symbol in self.non_terminals:
                        first |= (self.non_terminals[symbol].first - {'_'})
                        if '_' not in self.non_terminals[symbol].first:
                            nullable = False
                            break
                    else:
                        first.add(symbol)
                        nullable = False
                        break

                if nullable:
                    first.add('_')

                first_sets[tuple(prod)] = first

            # Verificar intersecciones entre todos los pares de producciones
            productions_list = list(first_sets.items())
            for i in range(len(productions_list)):
                for j in range(i + 1, len(productions_list)):
                    (prod1, first1), (prod2, first2) = productions_list[i], productions_list[j]
                    intersection = first1 & first2
                    if intersection:
                        conflict_key = f"{nt.value} → {' '.join(prod1)} | {nt.value} → {' '.join(prod2)}"
                        conflicts['first_conflicts'][conflict_key] = intersection
                        is_valid = False

        # Condición 2: Verificar FIRST ∩ FOLLOW para producciones ε
        for nt in self.non_terminals.values():
            has_epsilon = any('_' in prod for prod in nt.productions)
            if not has_epsilon:
                continue

            # Calcular FIRST del no terminal (sin ε)
            first = set()
            for prod in nt.productions:
                if prod == ['_']:
                    continue
                for symbol in prod:
                    if symbol in self.non_terminals:
                        first |= (self.non_terminals[symbol].first - {'_'})
                        if '_' not in self.non_terminals[symbol].first:
                            break
                    else:
                        first.add(symbol)
                        break

            # Verificar intersección con FOLLOW
            intersection = first & nt.follow
            if intersection:
                conflicts['follow_conflicts'][nt.value] = {
                    'first': first,
                    'follow': nt.follow,
                    'intersection': intersection
                }
                is_valid = False

        return is_valid, conflicts

    def get_terminals(self):
        return list(self.terminals.keys())
    def get_non_terminals(self):
        return list(self.non_terminals.keys())
    def get_first(self):
        return {nt.value: list(nt.first) for nt in self.non_terminals.values()}
    def get_follow(self):
        return {nt.value: list(nt.follow) for nt in self.non_terminals.values()}
    def get_conflict(self):
        conflicts = {
            'first_conflicts': {},
            'follow_conflicts': {}
        }
        for nt in self.non_terminals.values():
            if nt.value in conflicts['first_conflicts']:
                conflicts['first_conflicts'][nt.value] = list(nt.first)
            if nt.value in conflicts['follow_conflicts']:
                conflicts['follow_conflicts'][nt.value] = list(nt.follow)
        return conflicts

    def get_grammar(self):
        grammar_list = []
        grouped_rules = {}

        # Agrupar producciones por lhs
        for rule in self.rules:
            lhs = rule.left
            rhs = ' '.join(rule.right)

            if lhs not in grouped_rules:
                grouped_rules[lhs] = [rhs]
            else:
                grouped_rules[lhs].append(rhs)

        # Convertir al formato requerido
        for lhs, rhs_list in grouped_rules.items():
            grammar_list.append({
                "lhs": lhs,
                "rhs": rhs_list
            })

        return {"grammar": grammar_list}


def main():
    g = Grammar()
    g.load_from_file("grammar.txt")
    #g.load_from_string("S -> A a\nA -> _")
    g.compute_first()
    g.compute_follow()
    g.build_ll1_table()

    # g.print_first_follow()
    # g.print_table()
    # is_ll1, conflicts = g.is_ll1()
    #
    # if is_ll1:
    #     print("La gramática es LL(1)")
    # else:
    #     print("La gramática NO es LL(1)")
    #     if conflicts['first_conflicts']:
    #         print("\nConflictos en FIRST:")
    #         for prod, symbols in conflicts['first_conflicts'].items():
    #             print(f"  {prod}: {symbols}")
    #     if conflicts['follow_conflicts']:
    #         print("\nConflictos FIRST/FOLLOW:")
    #         for nt, data in conflicts['follow_conflicts'].items():
    #             print(f"  {nt}: FIRST ∩ FOLLOW = {data['intersection']}")
    #             print(f"     FIRST: {data['first']}")
    #             print(f"     FOLLOW: {data['follow']}")

    input_string = "a c"  # Ejemplo para tu gramática+
    #print(f"\nAnalizando cadena: '{input_string}'")
    success = g.parse_2(input_string)
    print(success)
    #print("\nResultado:", "Aceptada" if success else "Rechazada")






if __name__ == '__main__':
    main()