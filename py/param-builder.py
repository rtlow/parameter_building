import os
import shutil
import argparse
from dotenv import dotenv_values
import numpy as np
import yaml

def main():
    # arg parsing
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--input', type=str, required=True, help='Configuration .yaml file. See ../hyper-param for examples.')
    parser.add_argument('--dry-run', action='store_true', help='Prints parameter file, doit file, and Config file text rather than write to disk.')

    args = parser.parse_args()
    hyp_param_file = args.input
    dry_run = args.dry_run

    # output directory TODO: parse?
    base_out = '../param/'

    # dotenv parsing
    config = dotenv_values(".env")

    # Constants
    OMEGA_BARYON = 0.046026
    C = 300000 # km/s


    # TODO: better file pathing to account for different CWDs
    # file parts here

    # for parameter file
    # TODO: separate per sim type
    # param_part = '../file_parts/param.part'
    param_part = '../file_parts/param_DREAMS.part'
    hydro_part = '../file_parts/hydro.part'
    SIDM_part = '../file_parts/SIDM.part'

    # for submission script
    doit_part = '../file_parts/doit.part'

    # for Config.sh
    config_part = '../file_parts/Config.part'
    config_DM_part = '../file_parts/Config-DM.part'
    config_HY_part = '../file_parts/Config-Hydro.part'
    config_2cDM_part = '../file_parts/Config-2cDM.part'
    config_SIDM_part = '../file_parts/Config-SIDM.part'
    config_Double_part = '../file_parts/Config-DoublePrecision.part'

    # scatter matrices
    scatter_matrix_2cDM = '../file_parts/scatter_matrix_2cDM.txt'
    scatter_matrix_SIDM = '../file_parts/scatter_matrix_SIDM.txt'
    scatter_states_SIDM = '../file_parts/scatter_states_SIDM.txt'


    double_input = True # TODO: parse from param file


    with open(hyp_param_file, 'r') as f:
        d = yaml.load(f, Loader=yaml.SafeLoader)

    for code_directory, param_dict in d.items():
        
        directory = f'dir_{code_directory}'

        # can use subprocess to generate cross section files here
        if param_dict['DM_type'] != 'CDM':
            cross_section = f'{param_dict['power']}_sigma{param_dict['sigma']}'
            if param_dict['DM_type'] == '2cDM':
                vkick = f'Vkick{param_dict['V_k']:.2f}'

        # kick to another function to figure out what IC file to use, or just let user define
        if param_dict['type'] == 'box':
            job_label = f'L{param_dict['boxsize']}N{param_dict['N_part']}'
            ic_file = f'IC-L{param_dict['boxsize']}N{param_dict['N_part']}-{code_directory}'
            arepo_out = f'../param/arepo/boxes/'
        elif param_dict['type'] == 'DREAMS':
            job_label = f'DREAMS{param_dict['IC']}'
            ic_file = f'ics_{param_dict['IC']}'
            arepo_out = '../param/arepo/DREAMS_MW_zooms/'
        elif param_dict['type'] == 'zoom':
            job_label = f'{param_dict['IC']}'
            ic_file = f'ics_{param_dict['IC']}'
            arepo_out = f'../param/arepo/{param_dict['IC']}/'

        if param_dict['DM_type'] == 'CDM':
            job_string = param_dict['DM_type'] + f'_{job_label}_' + param_dict['hydro_type'] + '_' + directory
        elif param_dict['DM_type'] == '2cDM':
            job_string = param_dict['DM_type'] + f'_{job_label}_' + param_dict['hydro_type'] + '_' + cross_section + '_' + directory + '_' + vkick
        elif param_dict['DM_type'] == 'SIDM':
            job_string = param_dict['DM_type'] + f'_{job_label}_' + param_dict['hydro_type'] + '_' + cross_section + '_' + directory
        
        boxsize_kpc = param_dict['boxsize'] * 1000
        
        if param_dict['type'] == 'box':
            softening_length = boxsize_kpc / (29 * param_dict['N_part'] )
        else:
            softening_length = param_dict['softening_length']
        
        mem_size_MB = param_dict['mem_size'] * 1000 

        # creating output directory
        param_name = job_string + '.txt'
        out_dir = base_out + f'{job_string}/'

        try:
            os.mkdir(out_dir)
        except:
            print(f'{out_dir} already exists!')
        
        with open(param_part, 'r') as f:
            param_text = f.read()

        with open(doit_part, 'r') as f:
            doit_text = f.read()

        with open(config_part, 'r') as f:
            config_text = f.read()

        # replacing text in parameter file
        param_text = param_text.replace('{$IC-FILE}', ic_file)
        param_text = param_text.replace('{$JOBSTRING}', job_string)
        param_text = param_text.replace('{$MEMSIZE}', str(mem_size_MB))
        param_text = param_text.replace('{$CODE_DIR}', str(code_directory))
        param_text = param_text.replace('{$BOXSIZE}', str(boxsize_kpc))

        param_text = param_text.replace('{$SOFTENING_LENGTH}', str(softening_length))
        param_text = param_text.replace('{$SOFTENING_LENGTH_HALF}', str(softening_length / 2)) 

        # replacing text in config file

        # hacky thing for PM grid size right now
        if param_dict['type'] == 'box':
            N_eff = 256 if param_dict['N_part'] <= 256 else param_dict['N_part']
        else:
            N_eff = 512

        config_text = config_text.replace('{$PMGRID_SIZE}', str(N_eff))

        if double_input:
            with open(config_Double_part, 'r') as f:
                config_text += f.read()

        if param_dict['DM_type'] != 'CDM':
            with open(SIDM_part, 'r') as f:
                param_text += f.read()
        if param_dict['DM_type'] == '2cDM':
            with open(config_2cDM_part, 'r') as f:
                config_text += f.read()
        elif param_dict['DM_type'] == 'SIDM':
            with open(config_SIDM_part, 'r') as f:
                config_text += f.read()

        if param_dict['hydro_type'] == 'HY':
            hydro_flag = 1
            omega_baryon = OMEGA_BARYON
            with open(hydro_part, 'r') as f:
                param_text += f.read()
            with open(config_HY_part, 'r') as f:
                config_text += f.read()
        else:
            hydro_flag = 0
            omega_baryon = 0
            with open(config_DM_part, 'r') as f:
                config_text += f.read()
        param_text = param_text.replace('{$OMEGA_BARYON}', str(omega_baryon))
        param_text = param_text.replace('{$HY_FLAG}', str(hydro_flag))

        # replacing text in doit script
        doit_text = doit_text.replace('{__MEMSIZE__}', f'{param_dict['mem_size']}g')
        doit_text = doit_text.replace('{__JOBSTRING__}', job_string)
        doit_text = doit_text.replace('{__CODE_DIR__}', str(code_directory))
        doit_text = doit_text.replace('{__NODES__}', str(param_dict['nodes']))
        doit_text = doit_text.replace('{__PARAM_FILE__}', param_name)

        doit_text = doit_text.replace('{__EMAIL__}', config['EMAIL'])
        doit_text = doit_text.replace('{__LOG_DIR__}', config['LOG_DIR'])
        doit_text = doit_text.replace('{__OUT_DIR__}', config['OUT_DIR'])
        doit_text = doit_text.replace('{__CLUSTER_CONTENT_DIR__}', config['CLUSTER_CONTENT_DIR'])

        doit_restart_text = doit_text.replace('{__RESTART__}', str(1))
        doit_text = doit_text.replace('{__RESTART__}', str(0))

        if param_dict['DM_type'] == '2cDM':
            delm = 1/2 * (param_dict['V_k'])**2 / C**2

            scatter_states_text = f'0.0 {1 - param_dict['heavy_fraction']}\n{delm:.3} {param_dict['heavy_fraction']}\n'
            scatter_states_out = out_dir + 'scatter_states.txt'
            
            if not dry_run:
                with open(scatter_states_out, 'w') as f:
                    f.write(scatter_states_text)

                shutil.copyfile(scatter_matrix_2cDM, out_dir + 'scatter_matrix.txt')
        elif param_dict['DM_type'] == 'SIDM':  
            if not dry_run:
                shutil.copyfile(scatter_states_SIDM, out_dir + 'scatter_states.txt')
                
                shutil.copyfile(scatter_matrix_SIDM, out_dir + 'scatter_matrix.txt')

        param_out = out_dir + param_name
        param_out1 = arepo_out + param_name
        doit_out = out_dir + 'doit.sh'
        doit_restart_out = out_dir + 'doit-restart.sh'
        config_out = out_dir + 'Config.sh'

        print(out_dir)
        if not dry_run:
            with open(param_out, 'w') as f:
                f.write(param_text)
            with open(param_out1, 'w') as f:
                f.write(param_text)
            with open(doit_out, 'w') as f:
                f.write(doit_text)
            with open(doit_restart_out, 'w') as f:
                f.write(doit_restart_text)
            with open(config_out, 'w') as f:
                f.write(config_text)
        else:
            print(param_text)
            print(doit_text)
            print(config_text)


if __name__ == "__main__":
    main()