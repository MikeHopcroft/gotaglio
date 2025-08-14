import pytest
from gotaglio.bool_ops import evaluate_boolean_expression


class TestEvaluateBooleanExpression:
    """Test cases for the evaluate_boolean_expression function."""

    def test_simple_variables(self):
        """Test evaluation of simple boolean variables."""
        variables = {"A": True, "B": False, "C": True}
        
        assert evaluate_boolean_expression("A", variables) is True
        assert evaluate_boolean_expression("B", variables) is False
        assert evaluate_boolean_expression("C", variables) is True

    def test_and_operations(self):
        """Test AND (&&) operations."""
        variables = {"A": True, "B": False, "C": True}
        
        assert evaluate_boolean_expression("A && B", variables) is False
        assert evaluate_boolean_expression("A && C", variables) is True
        assert evaluate_boolean_expression("B && C", variables) is False
        assert evaluate_boolean_expression("B && B", variables) is False

    def test_or_operations(self):
        """Test OR (||) operations."""
        variables = {"A": True, "B": False, "C": True}
        
        assert evaluate_boolean_expression("A || B", variables) is True
        assert evaluate_boolean_expression("A || C", variables) is True
        assert evaluate_boolean_expression("B || C", variables) is True
        assert evaluate_boolean_expression("B || B", variables) is False

    def test_not_operations(self):
        """Test NOT (!) operations."""
        variables = {"A": True, "B": False, "C": True}
        
        assert evaluate_boolean_expression("!A", variables) is False
        assert evaluate_boolean_expression("!B", variables) is True
        assert evaluate_boolean_expression("!C", variables) is False

    def test_complex_expressions(self):
        """Test complex boolean expressions with multiple operators."""
        variables = {"A": True, "B": False, "C": True}
        
        assert evaluate_boolean_expression("!A || B", variables) is False
        assert evaluate_boolean_expression("A && !B", variables) is True
        assert evaluate_boolean_expression("(A || B) && C", variables) is True
        assert evaluate_boolean_expression("A && (B || C)", variables) is True
        assert evaluate_boolean_expression("!A && !B", variables) is False
        assert evaluate_boolean_expression("!(A && B)", variables) is True
        assert evaluate_boolean_expression("!(A || B)", variables) is False

    def test_operator_precedence(self):
        """Test operator precedence (NOT > AND > OR)."""
        variables = {"A": True, "B": False, "C": True}
        
        # NOT has highest precedence
        assert evaluate_boolean_expression("!A && B", variables) is False
        assert evaluate_boolean_expression("A && !B", variables) is True
        
        # AND has higher precedence than OR
        assert evaluate_boolean_expression("A || B && C", variables) is True  # A || (B && C)
        assert evaluate_boolean_expression("B && C || A", variables) is True  # (B && C) || A

    def test_parentheses(self):
        """Test that parentheses override operator precedence."""
        variables = {"A": True, "B": False, "C": True}
        
        assert evaluate_boolean_expression("(A || B) && C", variables) is True
        assert evaluate_boolean_expression("A || (B && C)", variables) is True
        assert evaluate_boolean_expression("!(A && B)", variables) is True
        assert evaluate_boolean_expression("(!A) && B", variables) is False

    def test_variable_names_with_underscores_and_numbers(self):
        """Test variable names with underscores, numbers, and hyphens."""
        variables = {
            "_var": True,
            "var_1": False,
            "VAR_2": True,
            "test-var": False,
            "a1b2": True
        }
        
        assert evaluate_boolean_expression("_var", variables) is True
        assert evaluate_boolean_expression("var_1", variables) is False
        assert evaluate_boolean_expression("VAR_2", variables) is True
        assert evaluate_boolean_expression("test-var", variables) is False
        assert evaluate_boolean_expression("a1b2", variables) is True
        assert evaluate_boolean_expression("_var && VAR_2", variables) is True
        assert evaluate_boolean_expression("var_1 || test-var", variables) is False

    def test_all_false_variables(self):
        """Test expressions with all false variables."""
        variables = {"A": False, "B": False, "C": False}
        
        assert evaluate_boolean_expression("A", variables) is False
        assert evaluate_boolean_expression("A && B", variables) is False
        assert evaluate_boolean_expression("A || B", variables) is False
        assert evaluate_boolean_expression("!A", variables) is True
        assert evaluate_boolean_expression("!A && !B", variables) is True
        assert evaluate_boolean_expression("!(A || B)", variables) is True

    def test_all_true_variables(self):
        """Test expressions with all true variables."""
        variables = {"A": True, "B": True, "C": True}
        
        assert evaluate_boolean_expression("A", variables) is True
        assert evaluate_boolean_expression("A && B", variables) is True
        assert evaluate_boolean_expression("A || B", variables) is True
        assert evaluate_boolean_expression("!A", variables) is False
        assert evaluate_boolean_expression("!A || !B", variables) is False
        assert evaluate_boolean_expression("!(A && B)", variables) is False

    def test_missing_variable(self):
        """Test that missing variables raise KeyError."""
        variables = {"A": True, "B": False}
        
        with pytest.raises(KeyError):
            evaluate_boolean_expression("C", variables)
            
        with pytest.raises(KeyError):
            evaluate_boolean_expression("A && C", variables)

    def test_empty_variables(self):
        """Test behavior with empty variables dictionary."""
        variables = {}
        
        with pytest.raises(KeyError):
            evaluate_boolean_expression("A", variables)

    def test_example_from_docstring(self):
        """Test the examples from the original commented code."""
        variables = {
            "A": True,
            "B": False,
            "C": True,
        }

        expressions_and_expected = [
            ("A && B", False),
            ("A || B", True),
            ("!A || B", False),
            ("A && !B", True),
            ("(A || B) && C", True)
        ]

        for expr, expected in expressions_and_expected:
            result = evaluate_boolean_expression(expr, variables)
            assert result == expected, f"Expression '{expr}' should evaluate to {expected}, got {result}"

    def test_nested_parentheses(self):
        """Test deeply nested expressions with multiple levels of parentheses."""
        variables = {"A": True, "B": False, "C": True, "D": False}
        
        assert evaluate_boolean_expression("((A && B) || C) && D", variables) is False
        assert evaluate_boolean_expression("A && ((B || C) && !D)", variables) is True
        assert evaluate_boolean_expression("!(!(A && !B) || !(C || D))", variables) is True

    def test_single_character_variables(self):
        """Test single character variable names."""
        variables = {"x": True, "y": False, "z": True}
        
        assert evaluate_boolean_expression("x", variables) is True
        assert evaluate_boolean_expression("y", variables) is False
        assert evaluate_boolean_expression("x && y", variables) is False
        assert evaluate_boolean_expression("x || z", variables) is True

    def test_whitespace_handling(self):
        """Test that expressions work correctly with various whitespace patterns."""
        variables = {"A": True, "B": False, "C": True}
        
        # Test expressions with extra spaces
        assert evaluate_boolean_expression("A  &&  B", variables) is False
        assert evaluate_boolean_expression("A||B", variables) is True
        assert evaluate_boolean_expression("  A  ", variables) is True
        assert evaluate_boolean_expression("A &&   B", variables) is False
        assert evaluate_boolean_expression("   A   ||   B   ", variables) is True
        
        # Test with tabs and mixed whitespace
        assert evaluate_boolean_expression("A\t&&\tB", variables) is False
        assert evaluate_boolean_expression("\tA\t||\tB\t", variables) is True
        
        # Test whitespace around parentheses
        assert evaluate_boolean_expression("( A && B )", variables) is False
        assert evaluate_boolean_expression("(  A  ||  B  )", variables) is True
        assert evaluate_boolean_expression("  (  A  &&  B  )  ", variables) is False
        
        # Test whitespace around NOT operator
        assert evaluate_boolean_expression("! A", variables) is False
        assert evaluate_boolean_expression("  !  A  ", variables) is False
        assert evaluate_boolean_expression("!   B", variables) is True
        
        # Test complex expressions with mixed whitespace
        assert evaluate_boolean_expression("  ( A   ||   B )   &&   C  ", variables) is True
        assert evaluate_boolean_expression("A && ( B ||   C)", variables) is True
        assert evaluate_boolean_expression("  !  A  ||  B  ", variables) is False
