import {
Button
} from "@mui/material";

export default function SettingsModal({
  children,
  modalOpen,
  setModalOpen,
  title="",
  handleSave,
}) {
  if (!modalOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 py-1 max-h-screen">
      <div className="bg-surface p-6 rounded-md shadow-lg w-full max-w-2xl max-h-screen  overflow-auto">
        <h2 className="text-lg font-semibold mb-4">{title}</h2>

        {children}

        <div className="flex justify-end gap-2 space-x-2 mt-6">
          <Button
            onClick={() => setModalOpen(false)}
            variant="outlined"
          >
            Cancel
          </Button>
          <Button
            onClick={handleSave}
            variant="contained"
            color="primary"
          >
            Save
          </Button>
        </div>
      </div>
    </div>
  );
}
