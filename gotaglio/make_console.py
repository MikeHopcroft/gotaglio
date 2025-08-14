from rich.console import Console
import sys
from rich.text import Text


class MakeConsole:
    """
    The MakeConsole class is a wrapper around the rich console library that provides intelligent output rendering based on the execution context. Here's what it does:

    **Primary Purpose:**
    It creates a console that can automatically detect whether code is running in a Jupyter notebook or a terminal and renders output appropriately for each environment.

    **Key Features:**
    1. Context-Aware Rendering
    In Jupyter notebooks: Uses IPython's display() module to show output in a single output cell
    In terminals: Uses rich console with ANSI escape sequences for colored/formatted output
    In non-interactive contexts (like file redirection): Strips ANSI codes and outputs plain text
    2. Content Type Support
    Supports three content types:
        * text/plain: Plain text with ANSI escape sequences
        * text/html: HTML output
        * text/markdown: Markdown output
    
    3. Output Consolidation
    In Jupyter notebooks, it consolidates multiple print statements into a single output cell instead of creating separate output sub-cells for each print.


    ## Design Rationale

    The class addresses several pain points:

    1. Jupyter notebook fragmentation: Normally each print() creates a new output cell, but this consolidates them
    2. Environment detection: Automatically adapts to whether you're in a notebook or terminal
    3. Format flexibility: Allows specifying output format (plain text, HTML, markdown)
    4. ANSI handling: Intelligently handles ANSI escape sequences based on context
    This is particularly useful for library code that needs to work well in both interactive notebooks and command-line environments, providing a consistent and optimal user experience in each context.
    """

    """
    The MakeConsole class configures a `rich` console object that records
    all output. The MakeConsole.render() method detects whether the code
    is running in a Jupyter notebook or terminal and renders the output
    accordingly. If running in a Jupyter notebook, it uses the IPython
    display module to show the output. If running in a terminal, it uses the
    rich console to print the output.

    Motivations for MakeConsole include:
        - When running in a notebook, would like to display the entire output
          in a single output sub cell. Normally in Jupyter notebooks, each
          print() or display() call creates a new output sub cell. When
          creating markdown, it is convenient to coalesce text from a number
          of print() calls into a single output sub cell.
        - Autodetecting the context to select `rich` rendering or IPython
          display.
        - Ability to specify the rendering format (e.g. text/plain, text/html,
          text/markdown).
        - Ability to generate text without ANSI escape sequences in
          non-interactive contexts (e.g. when redirecting output to a file).

    DESGIN NOTE: it would seem more natural for a function to construct a
    console wrapper object, with the content type passed to __init__(). This
    console could then be returned by the function for the caller to render.
    This approach was not chosen because the IPython paradigm is that functions
    return data objects, which are rendered by the notebook.
    """

    def __init__(self):
        """
        This is a single-use class. Initialize members to None so that we
        can ensure that the class is initialized only once in the __call__()
        method.

        The usage pattern is that a function will be passed an instance of
        MakeConsole, which it will initialize with a content type specifier
        (e.g "text/html"). This will configure and return a `rich` console
        configured to record all output to a buffer. The function will then
        call the console to generate output.

        When the function returns, the caller can use the render() method to
        display the output in the appropriate format for the context in which
        it is running.
        """
        self._console = None

    def __call__(self, content_type="text/plain"):
        """
        Supported content types:
            - text/plain: Plain text output with ANSI escape sequences
            - text/html: HTML output
            - text/markdown: Markdown output
        """
        supported_types = {"text/plain", "text/html", "text/markdown"}
        if content_type not in supported_types:
            raise ValueError(f"Unsupported content_type: {content_type}")

        if self._console:
            raise Exception(
                "Console already created. Call render() to show the output."
            )

        self._content_type = content_type
        self._console = Console(force_terminal=True)
        self._console.begin_capture()
        return self._console

    def render(self):
        if not self._console:
            raise Exception("render() called before initialization with __call()__")
        text = self._console.end_capture()

        # This code needs to run in a context that may or may not have IPython
        # available. Wrap import in a try/except block to handle the situation
        # where IPython is not available.
        try:
            from IPython import get_ipython
            from IPython.display import display, HTML, Markdown

            ipython = get_ipython()
            if ipython and "IPKernelApp" in ipython.config:
                # We appear to be running in a Jupyter notebook.
                # Strip off ANSI escape sequences that were added by the
                # rich console.
                stripped = Text.from_ansi(text).plain
                if self._content_type == "text/html":
                    display(HTML(stripped))
                elif self._content_type == "text/markdown":
                    display(Markdown(stripped))
                else:
                    # Use print() to display the ANSI escape sequences
                    # from the `rich` console.
                    print(text)
                return
        except Exception:
            # Fall through to the terminal case if IPython is not available.
            pass

        # Use print() to display the ANSI escape sequences
        # from the `rich` console.
        if sys.stdout.isatty():
            print(text)
        else:
            stripped = Text.from_ansi(text).plain
            print(stripped)
