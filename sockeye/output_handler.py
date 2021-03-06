# Copyright 2017 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You may not
# use this file except in compliance with the License. A copy of the License
# is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is distributed on
# an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either
# express or implied. See the License for the specific language governing
# permissions and limitations under the License.

from abc import ABC, abstractmethod
import sys
from typing import Optional

import sockeye.constants as C
import sockeye.data_io
import sockeye.inference
from sockeye.utils import plot_attention, print_attention_text, get_alignments


def get_output_handler(output_type: str,
                       output_fname: Optional[str],
                       sure_align_threshold: float) -> 'OutputHandler':
    """

    :param output_type: Type of output handler.
    :param output_fname: Output filename. If none sys.stdout is used.
    :param sure_align_threshold: Threshold to consider an alignment link as 'sure'.
    :raises: ValueError for unknown output_type.
    :return: Output handler.
    """
    output_stream = sys.stdout if output_fname is None else sockeye.data_io.smart_open(output_fname, mode='w')
    if output_type == C.OUTPUT_HANDLER_TRANSLATION:
        return StringOutputHandler(output_stream)
    elif output_type == C.OUTPUT_HANDLER_TRANSLATION_WITH_ALIGNMENTS:
        return StringWithAlignmentsOutputHandler(output_stream, sure_align_threshold)
    elif output_type == C.OUTPUT_HANDLER_BENCHMARK:
        return BenchmarkOutputHandler(output_stream)
    elif output_type == C.OUTPUT_HANDLER_ALIGN_PLOT:
        return AlignPlotHandler(plot_prefix="align" if output_fname is None else output_fname)
    elif output_type == C.OUTPUT_HANDLER_ALIGN_TEXT:
        return AlignTextHandler(sure_align_threshold)
    else:
        raise ValueError("unknown output type")


class OutputHandler(ABC):
    """
    Abstract output handler interface
    """

    @abstractmethod
    def handle(self,
               t_input: sockeye.inference.TranslatorInput,
               t_output: sockeye.inference.TranslatorOutput,
               t_walltime: float = 0.):
        """
        :param t_input: Translator input.
        :param t_output: Translator output.
        :param t_walltime: Total wall-clock time for translation.
        """
        pass


class StringOutputHandler(OutputHandler):
    """
    Output handler to write translation to a stream

    :param stream: Stream to write translations to (e.g. sys.stdout).
    """

    def __init__(self, stream):
        self.stream = stream

    def handle(self,
               t_input: sockeye.inference.TranslatorInput,
               t_output: sockeye.inference.TranslatorOutput,
               t_walltime: float = 0.):
        """
        :param t_input: Translator input.
        :param t_output: Translator output.
        :param t_walltime: Total walltime for translation.
        """
        self.stream.write("%s\n" % t_output.translation)
        self.stream.flush()


class StringWithAlignmentsOutputHandler(StringOutputHandler):
    """
    Output handler to write translations and alignments to a stream. Translation and alignment string
    are separated by a tab.
    Alignments are written in the format:
    <src_index>-<trg_index> ...
    An alignment link is included if its probability is above the threshold.

    :param stream: Stream to write translations and alignments to.
    :param threshold: Threshold for including alignment links.
    """

    def __init__(self, stream, threshold: float) -> None:
        super().__init__(stream)
        self.threshold = threshold

    def handle(self,
               t_input: sockeye.inference.TranslatorInput,
               t_output: sockeye.inference.TranslatorOutput,
               t_walltime: float = 0.):
        """
        :param t_input: Translator input.
        :param t_output: Translator output.
        :param t_walltime: Total wall-clock time for translation.
        """
        alignments = " ".join(
            ["%d-%d" % (s, t) for s, t in get_alignments(t_output.attention_matrix, threshold=self.threshold)])
        self.stream.write("%s\t%s\n" % (t_output.translation, alignments))
        self.stream.flush()


class BenchmarkOutputHandler(StringOutputHandler):
    """
    Output handler to write detailed benchmark information to a stream.

    :param stream: Stream to write translations to (e.g. sys.stdout).
    """

    def handle(self,
               t_input: sockeye.inference.TranslatorInput,
               t_output: sockeye.inference.TranslatorOutput,
               t_walltime: float = 0.):
        """
        :param t_input: Translator input.
        :param t_output: Translator output.
        :param t_walltime: Total walltime for translation.
        """
        self.stream.write("input=%s\toutput=%s\tinput_tokens=%d\toutput_tokens=%d\ttranslation_time=%0.4f\n" %
                          (t_input.sentence,
                           t_output.translation,
                           len(t_input.tokens),
                           len(t_output.tokens),
                           t_walltime))
        self.stream.flush()


class AlignPlotHandler(OutputHandler):
    """
    Output handler to plot alignment matrices to PNG files.

    :param plot_prefix: Prefix for generated PNG files.
    """

    def __init__(self, plot_prefix: str) -> None:
        self.plot_prefix = plot_prefix

    def handle(self,
               t_input: sockeye.inference.TranslatorInput,
               t_output: sockeye.inference.TranslatorOutput,
               t_walltime: float = 0.):
        """
        :param t_input: Translator input.
        :param t_output: Translator output.
        :param t_walltime: Total wall-clock time for translation.
        """
        plot_attention(t_output.attention_matrix,
                       t_input.tokens,
                       t_output.tokens,
                       "%s_%d.png" % (self.plot_prefix, t_input.id))


class AlignTextHandler(OutputHandler):
    """
    Output handler to write alignment matrices as ASCII art.

    :param threshold: Threshold for considering alignment links as sure.
    """

    def __init__(self, threshold: float) -> None:
        self.threshold = threshold

    def handle(self,
               t_input: sockeye.inference.TranslatorInput,
               t_output: sockeye.inference.TranslatorOutput,
               t_walltime: float = 0.):
        """
        :param t_input: Translator input.
        :param t_output: Translator output.
        :param t_walltime: Total wall-clock time for translation.
        """
        print_attention_text(t_output.attention_matrix,
                             t_input.tokens,
                             t_output.tokens,
                             self.threshold)
