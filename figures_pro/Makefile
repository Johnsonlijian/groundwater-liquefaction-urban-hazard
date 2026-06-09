.PHONY: doctor fig1 fig1-blender fig2 fig3 fig4 fig5 fig6 box1 all audit manifest

doctor:
	python python/doctor.py

fig1:
	python python/build_svg_suite.py --fig Fig1

fig1-blender:
	blender --background --python blender/render_fig1.py

fig2:
	python python/build_svg_suite.py --fig Fig2

fig3:
	python python/build_svg_suite.py --fig Fig3

fig4:
	python python/build_svg_suite.py --fig Fig4

fig5:
	python python/build_svg_suite.py --fig Fig5

fig6:
	python python/build_svg_suite.py --fig Fig6

box1:
	python python/build_svg_suite.py --fig Box1

all:
	python python/build_svg_suite.py
	python python/build_pptx_deck.py

audit:
	python python/audit_figures.py

manifest:
	python python/write_manifest.py
