from ._preview_utils import get_user_env_keycodes

class InputHandler:
    def __init__(self, key_preset: str = 'DEFAULT'):
        self.key_preset = key_preset

    def check_key_action(self, key_raw: int) -> str:
        key = key_raw & 0xFF

        env_keys = get_user_env_keycodes()

        key_mappings = {
            'DEFAULT': {
                'exit': [27],
                'pause': [32],
                'prev': [ord('a'), ord('A')],
                'next': [ord('d'), ord('D')],
                'first': [ord('w'), ord('W')],
                'last': [ord('s'), ord('S')],
                'zoom_in': [env_keys['ZOOM_IN']],
                'zoom_out': [env_keys['ZOOM_OUT']],
                'reset': [13],
                'pan_up': [env_keys['NUMPAD_8']],
                'pan_down': [env_keys['NUMPAD_2']],
                'pan_left': [env_keys['NUMPAD_4']],
                'pan_right': [env_keys['NUMPAD_6']],
                'pan_reset': [env_keys['NUMPAD_5']],
                'prev_comp': [env_keys['PAGE_UP']],
                'next_comp': [env_keys['PAGE_DOWN']],
            },
            'ARROW_ONLY': {
                'exit': [27], 'pause': [32],
                'prev': [env_keys['LEFT_ARROW'], env_keys['LEFT_ARROW_EX']],
                'next': [env_keys['RIGHT_ARROW'], env_keys['RIGHT_ARROW_EX']],
                'first': [env_keys['UP_ARROW'], env_keys['UP_ARROW_EX']],
                'last': [env_keys['DOWN_ARROW'], env_keys['DOWN_ARROW_EX']],
                'zoom_in': [env_keys['ZOOM_IN']],
                'zoom_out': [env_keys['ZOOM_OUT']],
                'reset': [13],
                'pan_up': [env_keys['NUMPAD_8']],
                'pan_down': [env_keys['NUMPAD_2']],
                'pan_left': [env_keys['NUMPAD_4']],
                'pan_right': [env_keys['NUMPAD_6']],
                'pan_reset': [env_keys['NUMPAD_5']],
                'prev_comp': [env_keys['PAGE_UP']],
                'next_comp': [env_keys['PAGE_DOWN']],
            },
            'ARROW_DEFAULT': {
                'exit': [27],
                'pause': [32],
                'prev': [env_keys['LEFT_ARROW'], env_keys['LEFT_ARROW_EX']],
                'next': [env_keys['RIGHT_ARROW'], env_keys['RIGHT_ARROW_EX']],
                'first': [env_keys['UP_ARROW'], env_keys['UP_ARROW_EX']],
                'last': [env_keys['DOWN_ARROW'], env_keys['DOWN_ARROW_EX']],
                'zoom_in': [env_keys['ZOOM_IN']],
                'zoom_out': [env_keys['ZOOM_OUT']],
                'reset': [13],
                'pan_up': [env_keys['NUMPAD_8']],
                'pan_down': [env_keys['NUMPAD_2']],
                'pan_left': [env_keys['NUMPAD_4']],
                'pan_right': [env_keys['NUMPAD_6']],
                'pan_reset': [env_keys['NUMPAD_5']],
                'prev_comp': [env_keys['PAGE_UP']],
                'next_comp': [env_keys['PAGE_DOWN']],
            }
        }

        current_mapping = key_mappings.get(self.key_preset, key_mappings['ARROW_DEFAULT'])

        for action, keys in current_mapping.items():
            if key in keys or key_raw in keys:
                return action

        return 'none'

    def get_controls_text(self) -> str:
        msg = 'Controls: '
        if self.key_preset == 'DEFAULT':
            msg += (
                f'SPACE(pause), '
                f'A/D(prev/next), '
                f'W/S(first/last), '
                f'+/-(zoom), '
                f'NumPad(pan), '
                f'PgUp/PgDn(comp), '
                f'ENTER(reset), '
                f'ESC(exit)'
            )
            return msg
        elif self.key_preset == 'ARROW_ONLY':
            msg += (
                f'SPACE(pause), '
                f'←/→(prev/next), '
                f'↑/↓(first/last), '
                f'+/-(zoom), '
                f'NumPad(pan), '
                f'PgUp/PgDn(comp), '
                f'ENTER(reset), '
                f'ESC(exit)'
            )
            return msg
        elif self.key_preset == 'ARROW_DEFAULT':
            msg += (
                f'SPACE(pause), '
                f'←/→(prev/next), '
                f'↑/↓(first/last), '
                f'+/-(zoom), '
                f'NumPad(pan), '
                f'PgUp/PgDn(comp), '
                f'ENTER(reset), '
                f'ESC(exit)'
            )
            return msg
        else:
            msg += (
                f'SPACE(pause), '
                f'A/D(prev/next), '
                f'W/S(first/last), '
                f'+/-(zoom), '
                f'NumPad(pan), '
                f'PgUp/PgDn(comp), '
                f'ENTER(reset), '
                f'ESC(exit)'
            )
            return msg
