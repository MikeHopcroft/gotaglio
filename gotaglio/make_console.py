from rich.console import Console
import sys
from rich.text import Text


class MakeConsole:
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
