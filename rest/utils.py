from .models import Column, Operation, FormulaStep, FormulaOperand


class FormulaParseError(Exception):
    pass


def parse_formula(formula_text, column, operations_dict):
    tokens = []
    i = 0
    while i < len(formula_text):
        char = formula_text[i]
        if char in '()+-*/':
            tokens.append(char)
        elif char == '%':
            tokens.append('%')
        elif char.lower() == 's' and formula_text[i:i+4].lower() == 'sqrt':
            tokens.append('sqrt')
            i += 3
        elif char.isspace():
            i += 1
            continue
        elif char.isdigit() or char == '.':
            num = ""
            while i < len(formula_text) and (formula_text[i].isdigit() or formula_text[i] == '.'):
                num += formula_text[i]
                i += 1
            tokens.append(float(num))
            continue
        else:
            col_name = ""
            while i < len(formula_text) and (formula_text[i].isalnum() or formula_text[i] == '_'):
                col_name += formula_text[i]
                i += 1
            if col_name:
                tokens.append(col_name)
            continue
        i += 1

    steps = []
    order = 0
    prev_operand = None

    for token in tokens:
        if token in operations_dict:
            operation = operations_dict[token]
            if prev_operand:
                step = FormulaStep(
                    column=column, operation=operation, operand=prev_operand, order=order)
                steps.append(step)
                order += 1
            prev_operand = None
        elif isinstance(token, float):
            operand = FormulaOperand(constant=token)
            operand.save()
            prev_operand = operand
        elif isinstance(token, str) and token not in '()':
            ref_column = Column.objects.filter(
                table=column.table, name=token).first()
            if not ref_column:
                ref_column = Column(table=column.table,
                                    name=token, data_type='number')
                ref_column.save()
            operand = FormulaOperand(column=ref_column)
            operand.save()
            prev_operand = operand

    for step in steps:
        step.save()

    return steps
