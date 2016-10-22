'''Structuring Text Renderer'''
from markdown import Markdown
md = Markdown(extensions=['fenced_code'])


class RendererCollection:
    """A class of collection of article renderers.

    To add renderers, call class method :meth:`RenderCollection.add_renderer`.
    """
    __renderer = {}

    class RenderedError(Exception):
        original_exception = None


    @classmethod
    def does_support(cls, ext):
        """Check if the renderer support a specific type of text."""
        return ext in cls.__renderer

    @classmethod
    def get_supported_renderers(cls):
        """Get supporting renderers list

        :return: a dictionary contains information of each renderers
        :rtype: generator
        """
        for ext, renderer in cls.__renderer.items():
            yield {
                'ext': ext,
                'name': renderer['name'],
                'description': renderer['description']
            }

    @classmethod
    def render(cls, ext, source):
        """Render forrmated text using renderer specified by ``ext``.

        :param ext: extension of rendering source
        :param source:
        :return: rendered text
        """
        if not cls.does_support(ext):
            raise RenderedError('This extension `%s` is not supported.' % ext)

        try:
            return cls.__renderer[ext]['func'](source)
        except Exception as ex:
            new_ex = RenderedError('Render error occurs: %s' % ex.message)
            new_ex.original_exception = ex
            raise new_ex

    @classmethod
    def add_renderer(cls, ext, name, description, render_method):
        """Use this interface to extend the renderer.

        :param ext: extension of this new format
        :param name: name of the new renderer
        :param description: description to the new renderer
        :param callable render_method: a method called to render the
            text, contain only one parameter: source text.
        """
        assert ext not in cls.__renderer, \
            'extension %s has been occupied' % ext
        cls.__renderer[ext] = {
            'name': name,
            'description': description,
            'func': render_method
        }

RendererCollection.add_renderer('md', 'Markdown', 'Markdown', md.convert)
